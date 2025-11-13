import os
import json
from datetime import datetime, timedelta, timezone

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Google Calendar API scope (needed for creating Meet links)
SCOPES = ["https://www.googleapis.com/auth/calendar"]


def get_service():
    """Authenticate and return Google Calendar service."""
    creds = None
    token_path = os.path.join(os.path.dirname(__file__), "token_meet.json")
    credentials_path = os.path.join(os.path.dirname(__file__), "credentials.json")
    
    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            # Check if credentials have all required scopes
            if creds and creds.scopes:
                required_scopes = set(SCOPES)
                actual_scopes = set(creds.scopes)
                if not required_scopes.issubset(actual_scopes):
                    # Missing required scopes, need to re-authenticate
                    creds = None
                    os.remove(token_path)
        except Exception:
            # If token is invalid, remove it and re-authenticate
            creds = None
            if os.path.exists(token_path):
                os.remove(token_path)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as token:
            token.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def create_meeting(
    service,
    summary,
    start_time,
    end_time,
    attendees=None,
    description="",
    calendar_id="primary",
    timezone="UTC",
):
    """
    Create a Google Meet meeting by creating a calendar event with Meet link.
    
    Args:
        service: Google Calendar service object
        summary: Meeting title/summary
        start_time: Start time (datetime object or ISO string)
        end_time: End time (datetime object or ISO string)
        attendees: List of email addresses to invite (optional)
        description: Meeting description (optional)
        calendar_id: Calendar ID (default: 'primary')
        timezone: Timezone string (default: 'UTC')
    
    Returns:
        Event object with Meet link
    """
    try:
        # Convert datetime objects to ISO format if needed
        if isinstance(start_time, datetime):
            start_time = start_time.isoformat()
        if isinstance(end_time, datetime):
            end_time = end_time.isoformat()
        
        # Prepare attendees list
        attendee_list = []
        if attendees:
            attendee_list = [{"email": email} for email in attendees]
        
        event = {
            "summary": summary,
            "description": description,
            "start": {
                "dateTime": start_time,
                "timeZone": timezone,
            },
            "end": {
                "dateTime": end_time,
                "timeZone": timezone,
            },
            "attendees": attendee_list,
            "conferenceData": {
                "createRequest": {
                    "requestId": f"meet-{datetime.now().timestamp()}",
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                }
            },
        }
        
        event = (
            service.events()
            .insert(calendarId=calendar_id, body=event, conferenceDataVersion=1)
            .execute()
        )
        
        meet_link = None
        if "conferenceData" in event and "entryPoints" in event["conferenceData"]:
            for entry in event["conferenceData"]["entryPoints"]:
                if entry.get("entryPointType") == "video":
                    meet_link = entry.get("uri")
                    break
        
        return {
            "id": event.get("id"),
            "summary": event.get("summary"),
            "start": event.get("start"),
            "end": event.get("end"),
            "meet_link": meet_link,
            "html_link": event.get("htmlLink"),
            "attendees": event.get("attendees", []),
        }
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


def create_meeting_now(service, summary, duration_minutes=30, attendees=None, description="", calendar_id="primary"):
    """
    Create a Google Meet meeting starting now.
    
    Args:
        service: Google Calendar service object
        summary: Meeting title/summary
        duration_minutes: Duration in minutes (default: 30)
        attendees: List of email addresses to invite (optional)
        description: Meeting description (optional)
        calendar_id: Calendar ID (default: 'primary')
    
    Returns:
        Event object with Meet link
    """
    start_time = datetime.now(timezone.utc)
    end_time = start_time + timedelta(minutes=duration_minutes)
    return create_meeting(service, summary, start_time, end_time, attendees, description, calendar_id, "UTC")


def create_meeting_at_time(
    service,
    summary,
    start_datetime,
    duration_minutes=30,
    attendees=None,
    description="",
    calendar_id="primary",
    timezone="UTC",
):
    """
    Create a Google Meet meeting at a specific time.
    
    Args:
        service: Google Calendar service object
        summary: Meeting title/summary
        start_datetime: Start datetime (datetime object or ISO string)
        duration_minutes: Duration in minutes (default: 30)
        attendees: List of email addresses to invite (optional)
        description: Meeting description (optional)
        calendar_id: Calendar ID (default: 'primary')
        timezone: Timezone string (default: 'UTC')
    
    Returns:
        Event object with Meet link
    """
    if isinstance(start_datetime, str):
        start_datetime = datetime.fromisoformat(start_datetime.replace("Z", "+00:00"))
    
    end_datetime = start_datetime + timedelta(minutes=duration_minutes)
    return create_meeting(service, summary, start_datetime, end_datetime, attendees, description, calendar_id, timezone)


def get_meeting(service, event_id, calendar_id="primary"):
    """
    Get a meeting/event by ID.
    
    Args:
        service: Google Calendar service object
        event_id: Event/meeting ID
        calendar_id: Calendar ID (default: 'primary')
    
    Returns:
        Event object with Meet link
    """
    try:
        event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        
        meet_link = None
        if "conferenceData" in event and "entryPoints" in event["conferenceData"]:
            for entry in event["conferenceData"]["entryPoints"]:
                if entry.get("entryPointType") == "video":
                    meet_link = entry.get("uri")
                    break
        
        return {
            "id": event.get("id"),
            "summary": event.get("summary"),
            "description": event.get("description"),
            "start": event.get("start"),
            "end": event.get("end"),
            "meet_link": meet_link,
            "html_link": event.get("htmlLink"),
            "attendees": event.get("attendees", []),
            "status": event.get("status"),
        }
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


def list_meetings(service, calendar_id="primary", max_results=10, time_min=None, time_max=None):
    """
    List upcoming meetings/events with Meet links.
    
    Args:
        service: Google Calendar service object
        calendar_id: Calendar ID (default: 'primary')
        max_results: Maximum number of meetings to return (default: 10)
        time_min: Minimum time for events (ISO string or datetime, optional)
        time_max: Maximum time for events (ISO string or datetime, optional)
    
    Returns:
        List of meeting objects with Meet links
    """
    try:
        if time_min is None:
            time_min = datetime.utcnow().isoformat() + "Z"
        elif isinstance(time_min, datetime):
            time_min = time_min.isoformat()
        
        if time_max and isinstance(time_max, datetime):
            time_max = time_max.isoformat()
        
        events_result = (
            service.events()
            .list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = events_result.get("items", [])
        
        meetings = []
        for event in events:
            # Only include events with Meet links
            meet_link = None
            if "conferenceData" in event and "entryPoints" in event["conferenceData"]:
                for entry in event["conferenceData"]["entryPoints"]:
                    if entry.get("entryPointType") == "video":
                        meet_link = entry.get("uri")
                        break
            
            # Include all events, but mark which have Meet links
            meetings.append({
                "id": event.get("id"),
                "summary": event.get("summary"),
                "start": event.get("start"),
                "end": event.get("end"),
                "meet_link": meet_link,
                "html_link": event.get("htmlLink"),
                "attendees": event.get("attendees", []),
            })
        
        return meetings
    except HttpError as error:
        print(f"An error occurred: {error}")
        return []


def update_meeting(
    service,
    event_id,
    summary=None,
    start_time=None,
    end_time=None,
    attendees=None,
    description=None,
    calendar_id="primary",
):
    """
    Update a meeting/event.
    
    Args:
        service: Google Calendar service object
        event_id: Event/meeting ID
        summary: New meeting title (optional)
        start_time: New start time (optional)
        end_time: New end time (optional)
        attendees: New list of attendees (optional)
        description: New description (optional)
        calendar_id: Calendar ID (default: 'primary')
    
    Returns:
        Updated event object
    """
    try:
        event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        
        if summary:
            event["summary"] = summary
        if description is not None:
            event["description"] = description
        if start_time:
            if isinstance(start_time, datetime):
                start_time = start_time.isoformat()
            if "start" not in event:
                event["start"] = {}
            event["start"]["dateTime"] = start_time
        if end_time:
            if isinstance(end_time, datetime):
                end_time = end_time.isoformat()
            if "end" not in event:
                event["end"] = {}
            event["end"]["dateTime"] = end_time
        if attendees is not None:
            event["attendees"] = [{"email": email} for email in attendees]
        
        updated_event = (
            service.events()
            .update(calendarId=calendar_id, eventId=event_id, body=event)
            .execute()
        )
        
        meet_link = None
        if "conferenceData" in updated_event and "entryPoints" in updated_event["conferenceData"]:
            for entry in updated_event["conferenceData"]["entryPoints"]:
                if entry.get("entryPointType") == "video":
                    meet_link = entry.get("uri")
                    break
        
        return {
            "id": updated_event.get("id"),
            "summary": updated_event.get("summary"),
            "start": updated_event.get("start"),
            "end": updated_event.get("end"),
            "meet_link": meet_link,
            "html_link": updated_event.get("htmlLink"),
            "attendees": updated_event.get("attendees", []),
        }
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


def delete_meeting(service, event_id, calendar_id="primary"):
    """
    Delete a meeting/event by ID.
    
    Args:
        service: Google Calendar service object
        event_id: Event/meeting ID
        calendar_id: Calendar ID (default: 'primary')
    
    Returns:
        True if successful, False otherwise
    """
    try:
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
        return True
    except HttpError as error:
        print(f"An error occurred: {error}")
        return False


def add_attendee(service, event_id, email, calendar_id="primary"):
    """
    Add an attendee to an existing meeting.
    
    Args:
        service: Google Calendar service object
        event_id: Event/meeting ID
        email: Email address of attendee to add
        calendar_id: Calendar ID (default: 'primary')
    
    Returns:
        Updated event object
    """
    try:
        event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        
        existing_attendees = [a.get("email") for a in event.get("attendees", [])]
        if email not in existing_attendees:
            event.setdefault("attendees", []).append({"email": email})
        
        updated_event = (
            service.events()
            .update(calendarId=calendar_id, eventId=event_id, body=event)
            .execute()
        )
        
        meet_link = None
        if "conferenceData" in updated_event and "entryPoints" in updated_event["conferenceData"]:
            for entry in updated_event["conferenceData"]["entryPoints"]:
                if entry.get("entryPointType") == "video":
                    meet_link = entry.get("uri")
                    break
        
        return {
            "id": updated_event.get("id"),
            "summary": updated_event.get("summary"),
            "meet_link": meet_link,
            "attendees": updated_event.get("attendees", []),
        }
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


def remove_attendee(service, event_id, email, calendar_id="primary"):
    """
    Remove an attendee from a meeting.
    
    Args:
        service: Google Calendar service object
        event_id: Event/meeting ID
        email: Email address of attendee to remove
        calendar_id: Calendar ID (default: 'primary')
    
    Returns:
        Updated event object
    """
    try:
        event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        
        event["attendees"] = [a for a in event.get("attendees", []) if a.get("email") != email]
        
        updated_event = (
            service.events()
            .update(calendarId=calendar_id, eventId=event_id, body=event)
            .execute()
        )
        
        meet_link = None
        if "conferenceData" in updated_event and "entryPoints" in updated_event["conferenceData"]:
            for entry in updated_event["conferenceData"]["entryPoints"]:
                if entry.get("entryPointType") == "video":
                    meet_link = entry.get("uri")
                    break
        
        return {
            "id": updated_event.get("id"),
            "summary": updated_event.get("summary"),
            "meet_link": meet_link,
            "attendees": updated_event.get("attendees", []),
        }
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


def main():
    """Example usage of Google Meet functions."""
    try:
        service = get_service()

        # 1. Create a meeting starting in 10 minutes
        start_time = datetime.now(timezone.utc) + timedelta(minutes=10)
        end_time = start_time + timedelta(minutes=30)
        meeting = create_meeting(
            service,
            "Team Sync Meeting",
            start_time,
            end_time,
            attendees=["example@gmail.com"],
            description="Weekly team sync",
        )
        if meeting:
            print(f"Created meeting: {json.dumps(meeting, indent=2)}")

        # 2. List upcoming meetings
        meetings = list_meetings(service, max_results=5)
        print(f"Found {len(meetings)} meetings")

        # 3. Get a specific meeting
        if meetings:
            meeting_details = get_meeting(service, meetings[0]["id"])
            if meeting_details:
                print(f"Meeting details: {json.dumps(meeting_details, indent=2)}")

    except HttpError as error:
        print("An error occurred:", error)


if __name__ == "__main__":
    main()

