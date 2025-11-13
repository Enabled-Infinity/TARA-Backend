"""
LLM Integration Tools Module

This module provides a reusable function to interact with OpenAI's GPT-5 model
with access to Google Workspace integrations (Gmail, Calendar, Docs, Drive, Meet, Sheets).

Usage:
    # As a module:
    from integrations.channels.main import process_llm_with_tools
    
    result = process_llm_with_tools("List my recent emails")
    print(result["output_text"])
    
    # From terminal:
    python main.py "List my recent emails"
    # or
    python main.py  # for interactive mode
"""

from openai import OpenAI
from dotenv import load_dotenv
import json
from datetime import datetime, timedelta, timezone

# Import integration functions
from gmail import (
    get_service as get_gmail_service,
    list_messages,
    get_message,
    get_message_content,
    send_email,
    send_email_with_attachment,
    delete_message,
    mark_as_read,
    mark_as_unread,
)
from google_calender import (
    get_service as get_calendar_service,
    list_events,
    create_event,
    update_event,
    delete_event,
)
from google_docs import (
    get_service as get_docs_service,
    get_drive_service,
    create_document,
    get_document,
    get_document_content,
    insert_text,
    replace_text,
    delete_text,
    format_text,
    list_documents,
    delete_document,
    share_document,
)
from google_drive import (
    get_service as get_drive_service_main,
    list_files,
    get_file,
    upload_file,
    upload_file_content,
    download_file,
    download_file_content,
    create_folder,
    update_file,
    delete_file as delete_drive_file,
    share_file,
    share_file_public,
    get_file_permissions,
    remove_permission,
    copy_file,
    search_files,
    get_folders,
)
from google_meet import (
    get_service as get_meet_service,
    create_meeting,
    create_meeting_now,
    create_meeting_at_time,
    get_meeting,
    list_meetings,
    update_meeting,
    delete_meeting,
    add_attendee,
    remove_attendee,
)
from google_sheets import (
    get_service as get_sheets_service,
    create_spreadsheet,
    get_spreadsheet,
    read_range,
    write_range,
    append_row,
    clear_range,
    batch_update,
    update_cell,
    get_cell,
    add_sheet,
    delete_sheet,
    format_cells,
    set_column_width,
    set_row_height,
    batch_read,
    batch_write,
    get_sheet_info,
)

load_dotenv()
client = OpenAI()

# Service cache to avoid re-authenticating
_service_cache = {}


def get_cached_service(service_type):
    """Get or create a cached service instance."""
    if service_type not in _service_cache:
        if service_type == "gmail":
            print('GMAIL')
            _service_cache[service_type] = get_gmail_service()
        elif service_type == "calendar":
            print('CALENDAR')
            _service_cache[service_type] = get_calendar_service()
        elif service_type == "docs":
            print('DOCS')
            _service_cache[service_type] = get_docs_service()
        elif service_type == "drive":
            print('DRIVE')
            _service_cache[service_type] = get_drive_service_main()
        elif service_type == "meet":
            print('MEET')
            _service_cache[service_type] = get_meet_service()
        elif service_type == "sheets":
            print('SHEETS')
            _service_cache[service_type] = get_sheets_service()
    return _service_cache[service_type]


# Define tools for OpenAI
tools = [
    # Gmail tools
    {
        "type": "function",
        "name": "gmail_list_messages",
        "description": "List messages from Gmail inbox. Can filter by query (e.g., 'from:example@gmail.com', 'subject:test').",
        "parameters": {
            "type": "object",
            "properties": {
                "max_results": {"type": "integer", "description": "Maximum number of messages to return (default: 10)"},
                "query": {"type": "string", "description": "Gmail search query (optional)"},
            },
        },
    },
    {
        "type": "function",
        "name": "gmail_get_message",
        "description": "Get a specific Gmail message by ID with full content.",
        "parameters": {
            "type": "object",
            "properties": {
                "message_id": {"type": "string", "description": "ID of the message to retrieve"},
            },
            "required": ["message_id"],
        },
    },
    {
        "type": "function",
        "name": "gmail_send_email",
        "description": "Send an email via Gmail.",
        "parameters": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string", "description": "Email subject"},
                "body": {"type": "string", "description": "Email body content"},
                "is_html": {"type": "boolean", "description": "Whether the body is HTML (default: false)"},
            },
            "required": ["to", "subject", "body"],
        },
    },
    {
        "type": "function",
        "name": "gmail_mark_as_read",
        "description": "Mark a Gmail message as read.",
        "parameters": {
            "type": "object",
            "properties": {
                "message_id": {"type": "string", "description": "ID of the message to mark as read"},
            },
            "required": ["message_id"],
        },
    },
    {
        "type": "function",
        "name": "gmail_delete_message",
        "description": "Delete a Gmail message by ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "message_id": {"type": "string", "description": "ID of the message to delete"},
            },
            "required": ["message_id"],
        },
    },
    # Google Calendar tools
    {
        "type": "function",
        "name": "calendar_list_events",
        "description": "List upcoming events from Google Calendar.",
        "parameters": {
            "type": "object",
            "properties": {
                "max_results": {"type": "integer", "description": "Maximum number of events to return (default: 10)"},
            },
        },
    },
    {
        "type": "function",
        "name": "calendar_create_event",
        "description": "Create a new event in Google Calendar. Start and end times should be in ISO format (e.g., '2024-01-15T10:00:00Z').",
        "parameters": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "Event title/summary"},
                "start_time": {"type": "string", "description": "Start time in ISO format"},
                "end_time": {"type": "string", "description": "End time in ISO format"},
                "description": {"type": "string", "description": "Event description (optional)"},
            },
            "required": ["summary", "start_time", "end_time"],
        },
    },
    {
        "type": "function",
        "name": "calendar_delete_event",
        "description": "Delete an event from Google Calendar by ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "event_id": {"type": "string", "description": "ID of the event to delete"},
            },
            "required": ["event_id"],
        },
    },
    # Google Docs tools
    {
        "type": "function",
        "name": "docs_create_document",
        "description": "Create a new Google Doc.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Title of the document"},
            },
        },
    },
    {
        "type": "function",
        "name": "docs_get_document",
        "description": "Get a Google Doc by ID and return its content.",
        "parameters": {
            "type": "object",
            "properties": {
                "document_id": {"type": "string", "description": "ID of the document to retrieve"},
            },
            "required": ["document_id"],
        },
    },
    {
        "type": "function",
        "name": "docs_insert_text",
        "description": "Insert text into a Google Doc at a specific index.",
        "parameters": {
            "type": "object",
            "properties": {
                "document_id": {"type": "string", "description": "ID of the document"},
                "text": {"type": "string", "description": "Text to insert"},
                "index": {"type": "integer", "description": "Character index where to insert (default: 1)"},
            },
            "required": ["document_id", "text"],
        },
    },
    {
        "type": "function",
        "name": "docs_list_documents",
        "description": "List Google Docs documents.",
        "parameters": {
            "type": "object",
            "properties": {
                "max_results": {"type": "integer", "description": "Maximum number of documents to return (default: 10)"},
            },
        },
    },
    # Google Drive tools
    {
        "type": "function",
        "name": "drive_list_files",
        "description": "List files in Google Drive. Can filter by query (e.g., \"name contains 'test'\", \"mimeType='application/pdf'\").",
        "parameters": {
            "type": "object",
            "properties": {
                "page_size": {"type": "integer", "description": "Maximum number of files to return (default: 10)"},
                "query": {"type": "string", "description": "Search query (optional)"},
            },
        },
    },
    {
        "type": "function",
        "name": "drive_get_file",
        "description": "Get file metadata by ID from Google Drive.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_id": {"type": "string", "description": "ID of the file to retrieve"},
            },
            "required": ["file_id"],
        },
    },
    {
        "type": "function",
        "name": "drive_create_folder",
        "description": "Create a folder in Google Drive.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name of the folder"},
            },
            "required": ["name"],
        },
    },
    {
        "type": "function",
        "name": "drive_search_files",
        "description": "Search for files in Google Drive using a query.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query (e.g., \"name contains 'test'\", \"mimeType='application/pdf'\")"},
                "page_size": {"type": "integer", "description": "Maximum number of results (default: 10)"},
            },
            "required": ["query"],
        },
    },
    # Google Meet tools
    {
        "type": "function",
        "name": "meet_create_meeting",
        "description": "Create a Google Meet meeting. Start and end times should be in ISO format (e.g., '2024-01-15T10:00:00Z').",
        "parameters": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "Meeting title/summary"},
                "start_time": {"type": "string", "description": "Start time in ISO format"},
                "end_time": {"type": "string", "description": "End time in ISO format"},
                "attendees": {"type": "array", "items": {"type": "string"}, "description": "List of email addresses to invite (optional)"},
                "description": {"type": "string", "description": "Meeting description (optional)"},
            },
            "required": ["summary", "start_time", "end_time"],
        },
    },
    {
        "type": "function",
        "name": "meet_create_meeting_now",
        "description": "Create a Google Meet meeting starting now.",
        "parameters": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "Meeting title/summary"},
                "duration_minutes": {"type": "integer", "description": "Duration in minutes (default: 30)"},
                "attendees": {"type": "array", "items": {"type": "string"}, "description": "List of email addresses to invite (optional)"},
                "description": {"type": "string", "description": "Meeting description (optional)"},
            },
            "required": ["summary"],
        },
    },
    {
        "type": "function",
        "name": "meet_list_meetings",
        "description": "List upcoming Google Meet meetings.",
        "parameters": {
            "type": "object",
            "properties": {
                "max_results": {"type": "integer", "description": "Maximum number of meetings to return (default: 10)"},
            },
        },
    },
    {
        "type": "function",
        "name": "meet_get_meeting",
        "description": "Get a Google Meet meeting by event ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "event_id": {"type": "string", "description": "Event/meeting ID"},
            },
            "required": ["event_id"],
        },
    },
    # Google Sheets tools
    {
        "type": "function",
        "name": "sheets_create_spreadsheet",
        "description": "Create a new Google Spreadsheet.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Title of the spreadsheet"},
            },
        },
    },
    {
        "type": "function",
        "name": "sheets_read_range",
        "description": "Read data from a specific range in a spreadsheet. Range should be in A1 notation (e.g., 'Sheet1!A1:B10').",
        "parameters": {
            "type": "object",
            "properties": {
                "spreadsheet_id": {"type": "string", "description": "ID of the spreadsheet"},
                "range_name": {"type": "string", "description": "A1 notation range (e.g., 'Sheet1!A1:B10')"},
            },
            "required": ["spreadsheet_id", "range_name"],
        },
    },
    {
        "type": "function",
        "name": "sheets_write_range",
        "description": "Write data to a specific range in a spreadsheet. Values should be a 2D array (list of rows).",
        "parameters": {
            "type": "object",
            "properties": {
                "spreadsheet_id": {"type": "string", "description": "ID of the spreadsheet"},
                "range_name": {"type": "string", "description": "A1 notation range (e.g., 'Sheet1!A1:B10')"},
                "values": {"type": "array", "items": {"type": "array", "items": {"type": "string"}}, "description": "List of rows (each row is a list of cell values)"},
            },
            "required": ["spreadsheet_id", "range_name", "values"],
        },
    },
    {
        "type": "function",
        "name": "sheets_append_row",
        "description": "Append a row to the end of a range in a spreadsheet.",
        "parameters": {
            "type": "object",
            "properties": {
                "spreadsheet_id": {"type": "string", "description": "ID of the spreadsheet"},
                "range_name": {"type": "string", "description": "A1 notation range (e.g., 'Sheet1!A1:B')"},
                "values": {"type": "array", "items": {"type": "string"}, "description": "List of cell values for the row"},
            },
            "required": ["spreadsheet_id", "range_name", "values"],
        },
    },
    {"type": "web_search"}
]


# Wrapper functions that can be called by OpenAI
def gmail_list_messages(max_results=10, query=""):
    """List messages from Gmail inbox."""
    service = get_cached_service("gmail")
    messages = list_messages(service, max_results=max_results, query=query)
    return json.dumps({"messages": messages}, indent=2)


def gmail_get_message(message_id):
    """Get a specific Gmail message by ID."""
    service = get_cached_service("gmail")
    message = get_message(service, message_id)
    if message:
        content = get_message_content(message)
        return json.dumps(content, indent=2)
    return json.dumps({"error": "Message not found"})


def gmail_send_email(to, subject, body, is_html=False):
    """Send an email via Gmail."""
    service = get_cached_service("gmail")
    result = send_email(service, to, subject, body, is_html=is_html)
    if result:
        return json.dumps({"success": True, "message_id": result.get("id")}, indent=2)
    return json.dumps({"success": False, "error": "Failed to send email"})


def gmail_mark_as_read(message_id):
    """Mark a Gmail message as read."""
    service = get_cached_service("gmail")
    result = mark_as_read(service, message_id)
    if result:
        return json.dumps({"success": True}, indent=2)
    return json.dumps({"success": False, "error": "Failed to mark as read"})


def gmail_delete_message(message_id):
    """Delete a Gmail message by ID."""
    service = get_cached_service("gmail")
    result = delete_message(service, message_id)
    return json.dumps({"success": result}, indent=2)


def calendar_list_events(max_results=10):
    """List upcoming events from Google Calendar."""
    service = get_cached_service("calendar")
    events = list_events(service, max_results=max_results)
    return json.dumps({"events": events}, indent=2)


def calendar_create_event(summary, start_time, end_time, description=""):
    """Create a new event in Google Calendar."""
    service = get_cached_service("calendar")
    # Parse ISO format strings to datetime if needed
    if isinstance(start_time, str):
        start_time = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
    if isinstance(end_time, str):
        end_time = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
    
    event = {
        "summary": summary,
        "description": description,
        "start": {"dateTime": start_time.isoformat(), "timeZone": "UTC"},
        "end": {"dateTime": end_time.isoformat(), "timeZone": "UTC"},
    }
    result = service.events().insert(calendarId="primary", body=event).execute()
    return json.dumps({"id": result.get("id"), "htmlLink": result.get("htmlLink")}, indent=2)


def calendar_delete_event(event_id):
    """Delete an event from Google Calendar."""
    service = get_cached_service("calendar")
    delete_event(service, event_id)
    return json.dumps({"success": True}, indent=2)


def docs_create_document(title="Untitled Document"):
    """Create a new Google Doc."""
    service = get_cached_service("docs")
    result = create_document(service, title)
    if result:
        return json.dumps(result, indent=2)
    return json.dumps({"error": "Failed to create document"})


def docs_get_document(document_id):
    """Get a Google Doc by ID and return its content."""
    service = get_cached_service("docs")
    doc = get_document(service, document_id)
    if doc:
        content = get_document_content(doc)
        return json.dumps(content, indent=2)
    return json.dumps({"error": "Document not found"})


def docs_insert_text(document_id, text, index=1):
    """Insert text into a Google Doc."""
    service = get_cached_service("docs")
    result = insert_text(service, document_id, text, index)
    if result:
        return json.dumps({"success": True}, indent=2)
    return json.dumps({"error": "Failed to insert text"})


def docs_list_documents(max_results=10):
    """List Google Docs documents."""
    drive_service = get_drive_service()  # Uses get_drive_service from google_docs
    documents = list_documents(drive_service, max_results=max_results)
    return json.dumps({"documents": documents}, indent=2)


def drive_list_files(page_size=10, query=""):
    """List files in Google Drive."""
    service = get_cached_service("drive")
    files = list_files(service, page_size=page_size, query=query)
    return json.dumps({"files": files}, indent=2)


def drive_get_file(file_id):
    """Get file metadata by ID from Google Drive."""
    service = get_cached_service("drive")
    file = get_file(service, file_id)
    if file:
        return json.dumps(file, indent=2)
    return json.dumps({"error": "File not found"})


def drive_create_folder(name):
    """Create a folder in Google Drive."""
    service = get_cached_service("drive")
    folder = create_folder(service, name)
    if folder:
        return json.dumps(folder, indent=2)
    return json.dumps({"error": "Failed to create folder"})


def drive_search_files(query, page_size=10):
    """Search for files in Google Drive."""
    service = get_cached_service("drive")
    files = search_files(service, query, page_size=page_size)
    return json.dumps({"files": files}, indent=2)


def meet_create_meeting(summary, start_time, end_time, attendees=None, description=""):
    """Create a Google Meet meeting."""
    service = get_cached_service("meet")
    # Parse ISO format strings to datetime if needed
    if isinstance(start_time, str):
        start_time = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
    if isinstance(end_time, str):
        end_time = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
    
    result = create_meeting(service, summary, start_time, end_time, attendees, description)
    if result:
        return json.dumps(result, indent=2)
    return json.dumps({"error": "Failed to create meeting"})


def meet_create_meeting_now(summary, duration_minutes=30, attendees=None, description=""):
    """Create a Google Meet meeting starting now."""
    service = get_cached_service("meet")
    result = create_meeting_now(service, summary, duration_minutes, attendees, description)
    if result:
        return json.dumps(result, indent=2)
    return json.dumps({"error": "Failed to create meeting"})


def meet_list_meetings(max_results=10):
    """List upcoming Google Meet meetings."""
    service = get_cached_service("meet")
    meetings = list_meetings(service, max_results=max_results)
    return json.dumps({"meetings": meetings}, indent=2)


def meet_get_meeting(event_id):
    """Get a Google Meet meeting by event ID."""
    service = get_cached_service("meet")
    meeting = get_meeting(service, event_id)
    if meeting:
        return json.dumps(meeting, indent=2)
    return json.dumps({"error": "Meeting not found"})


def sheets_create_spreadsheet(title="Untitled Spreadsheet"):
    """Create a new Google Spreadsheet."""
    service = get_cached_service("sheets")
    result = create_spreadsheet(service, title)
    if result:
        return json.dumps(result, indent=2)
    return json.dumps({"error": "Failed to create spreadsheet"})


def sheets_read_range(spreadsheet_id, range_name):
    """Read data from a specific range in a spreadsheet."""
    service = get_cached_service("sheets")
    values = read_range(service, spreadsheet_id, range_name)
    return json.dumps({"values": values}, indent=2)


def sheets_write_range(spreadsheet_id, range_name, values):
    """Write data to a specific range in a spreadsheet."""
    service = get_cached_service("sheets")
    result = write_range(service, spreadsheet_id, range_name, values)
    if result:
        return json.dumps({"success": True, "updated_cells": result.get("updatedCells")}, indent=2)
    return json.dumps({"error": "Failed to write to spreadsheet"})


def sheets_append_row(spreadsheet_id, range_name, values):
    """Append a row to the end of a range in a spreadsheet."""
    service = get_cached_service("sheets")
    result = append_row(service, spreadsheet_id, range_name, values)
    if result:
        return json.dumps({"success": True}, indent=2)
    return json.dumps({"error": "Failed to append row"})


# Map function names to their implementations
function_map = {
    "gmail_list_messages": gmail_list_messages,
    "gmail_get_message": gmail_get_message,
    "gmail_send_email": gmail_send_email,
    "gmail_mark_as_read": gmail_mark_as_read,
    "gmail_delete_message": gmail_delete_message,
    "calendar_list_events": calendar_list_events,
    "calendar_create_event": calendar_create_event,
    "calendar_delete_event": calendar_delete_event,
    "docs_create_document": docs_create_document,
    "docs_get_document": docs_get_document,
    "docs_insert_text": docs_insert_text,
    "docs_list_documents": docs_list_documents,
    "drive_list_files": drive_list_files,
    "drive_get_file": drive_get_file,
    "drive_create_folder": drive_create_folder,
    "drive_search_files": drive_search_files,
    "meet_create_meeting": meet_create_meeting,
    "meet_create_meeting_now": meet_create_meeting_now,
    "meet_list_meetings": meet_list_meetings,
    "meet_get_meeting": meet_get_meeting,
    "sheets_create_spreadsheet": sheets_create_spreadsheet,
    "sheets_read_range": sheets_read_range,
    "sheets_write_range": sheets_write_range,
    "sheets_append_row": sheets_append_row,
}


def filter_input_item(item_dict, valid_input_fields):
    """Filter dictionary to only include valid input fields."""
    if isinstance(item_dict, dict):
        filtered = {}
        for key, value in item_dict.items():
            if key in valid_input_fields:
                filtered[key] = value
        return filtered
    return item_dict


def process_llm_with_tools(
    user_message,
    model="gpt-5",
    instructions="You are a helpful assistant that can interact with Gmail, Google Calendar, Google Docs, Google Drive, Google Meet, and Google Sheets. Use the available tools to help users with their requests.",
    conversation_history=None,
    stream=True,
    max_iterations=10
):
    """
    Process a user message with LLM and integration tools.
    
    Args:
        user_message: The user's message/query
        model: OpenAI model to use (default: "gpt-5")
        instructions: System instructions for the model
        conversation_history: Optional list of previous messages in the conversation
        max_iterations: Maximum number of function calling iterations (default: 10)
    
    Returns:
        dict with 'response' (final response object) and 'output_text' (text output)
    """
    # Initialize conversation history
    if conversation_history is None:
        input_list = []
    else:
        input_list = conversation_history.copy()
    
    # Add user message
    input_list.append({"role": "user", "content": user_message})
    
    # Valid fields for input parameter
    valid_input_fields = {'role', 'content', 'type', 'call_id', 'output', 'name', 'arguments'}
    
    # Iterate until we get a final response (or hit max iterations)
    iteration = 0
    while iteration < max_iterations:
        iteration += 1
        
        # Get response from model
        response = client.responses.create(
            model=model,
            tools=tools,
            input=input_list,
            instructions=instructions if iteration == 1 else None,  # Only send instructions on first call
        )
        
        # Convert response items to dictionaries and filter
        for item in response.output:
            # Skip reasoning items - they're internal to the model
            if hasattr(item, 'type') and item.type == "reasoning":
                continue
                
            if hasattr(item, 'model_dump'):
                item_dict = item.model_dump()
                filtered_dict = filter_input_item(item_dict, valid_input_fields)
                if filtered_dict:
                    input_list.append(filtered_dict)
            else:
                # Fallback: convert to dict manually
                item_dict = {}
                if hasattr(item, 'type'):
                    item_dict['type'] = item.type
                if hasattr(item, 'content'):
                    item_dict['content'] = item.content
                if hasattr(item, 'name'):
                    item_dict['name'] = item.name
                if hasattr(item, 'arguments'):
                    item_dict['arguments'] = item.arguments
                if hasattr(item, 'call_id'):
                    item_dict['call_id'] = item.call_id
                if hasattr(item, 'role'):
                    item_dict['role'] = item.role
                if item_dict:
                    input_list.append(item_dict)
        
        # Check if we have function calls to process
        has_function_calls = False
        for item in response.output:
            if hasattr(item, 'type') and item.type == "function_call":
                has_function_calls = True
                function_name = item.name
                if function_name in function_map:
                    try:
                        # Parse arguments
                        args = json.loads(item.arguments) if isinstance(item.arguments, str) else item.arguments
                        
                        # Call the function
                        function_result = function_map[function_name](**args)
                        
                        # Provide function call results to the model
                        input_list.append({
                            "type": "function_call_output",
                            "call_id": item.call_id,
                            "output": function_result
                        })
                    except Exception as e:
                        # Handle errors
                        input_list.append({
                            "type": "function_call_output",
                            "call_id": item.call_id,
                            "output": json.dumps({"error": str(e)}, indent=2)
                        })
                else:
                    input_list.append({
                        "type": "function_call_output",
                        "call_id": item.call_id,
                        "output": json.dumps({"error": f"Unknown function: {function_name}"}, indent=2)
                    })
        
        # If no function calls, we're done
        if not has_function_calls:
            break
    
    return {
        "response": response,
        "output_text": response.output_text if hasattr(response, 'output_text') else None,
        "conversation_history": input_list
    }


# CLI interface for terminal usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Get message from command line arguments
        user_message = " ".join(sys.argv[1:])
    else:
        # Interactive mode
        user_message = input("Enter your message: ")
    
    result = process_llm_with_tools(user_message)
    
    print("\n" + "="*50)
    print("Response:")
    print("="*50)
    if result["output_text"]:
        print(result["output_text"])
    else:
        print(result["response"].model_dump_json(indent=2))

