import os
import json
from datetime import datetime, timedelta, timezone

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Google Calendar API scope (full access)
SCOPES = ["https://www.googleapis.com/auth/calendar"]


def get_service():
    """Authenticate and return Google Calendar service."""
    creds = None
    token_path = os.path.join(os.path.dirname(__file__), "token_calendar.json")
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


def list_events(service, calendar_id="primary", max_results=10):
    """List upcoming events."""
    now = datetime.utcnow().isoformat() + "Z"
    events_result = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=now,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    events = events_result.get("items", [])

    if not events:
        print("No upcoming events found.")
        return []

    print("Upcoming events:")
    for event in events:
        start = event["start"].get("dateTime", event["start"].get("date"))
        print(f"- {start} | {event.get('summary', '(no title)')}")
    return events


def create_event(service, calendar_id="primary"):
    """Create a sample event 10 mins from now for 30 mins."""
    start_time = datetime.now(timezone.utc) + timedelta(minutes=10)
    end_time = start_time + timedelta(minutes=30)

    event = {
        "summary": "Python API Demo Event",
        "description": "This event was created using Python + Google Calendar API",
        "start": {"dateTime": start_time.isoformat(), "timeZone": "UTC"},
        "end": {"dateTime": end_time.isoformat(), "timeZone": "UTC"},
    }

    event = service.events().insert(calendarId=calendar_id, body=event).execute()
    print("Event created:")
    print(json.dumps({"id": event["id"], "htmlLink": event["htmlLink"]}, indent=2))
    return event


def update_event(service, event_id, calendar_id="primary"):
    """Update the event summary and description."""
    event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()

    event["summary"] = "Updated Event Title"
    event["description"] = "Event updated using Python script."

    updated_event = (
        service.events().update(calendarId=calendar_id, eventId=event_id, body=event).execute()
    )
    print("Event updated:")
    print(json.dumps({"id": updated_event["id"], "htmlLink": updated_event["htmlLink"]}, indent=2))
    return updated_event


def delete_event(service, event_id, calendar_id="primary"):
    """Delete an event by ID."""
    service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
    print(f"Deleted event: {event_id}")


def main():
    try:
        service = get_service()

        # 1. List upcoming events
        list_events(service)

        # 2. Create a new event
        created = create_event(service)

        # 3. Update the same event
        update_event(service, created["id"])

        # 4. Delete the event (cleanup)
        delete_event(service, created["id"])

    except HttpError as error:
        print("An error occurred:", error)


if __name__ == "__main__":
    main()