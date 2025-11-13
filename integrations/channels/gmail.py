import os
import json
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Gmail API scope (full access)
# Using gmail.modify which is more commonly enabled and provides read/write access
# Alternative: ["https://www.googleapis.com/auth/gmail"] for full access
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


def get_service():
    """Authenticate and return Gmail service."""
    creds = None
    token_path = os.path.join(os.path.dirname(__file__), "token_gmail.json")
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
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Error refreshing token: {e}")
                # If refresh fails, re-authenticate
                creds = None
                if os.path.exists(token_path):
                    os.remove(token_path)
        
        if not creds or not creds.valid:
            try:
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
            except Exception as e:
                error_msg = str(e)
                if "invalid_scope" in error_msg.lower() or "invalid scope" in error_msg.lower():
                    print("\n" + "="*60)
                    print("ERROR: Gmail API scope is not enabled in your Google Cloud project.")
                    print("="*60)
                    print("\nTo fix this:")
                    print("1. Go to https://console.cloud.google.com/")
                    print("2. Select your project")
                    print("3. Navigate to 'APIs & Services' > 'Library'")
                    print("4. Search for 'Gmail API' and enable it")
                    print("5. Go to 'APIs & Services' > 'OAuth consent screen'")
                    print("6. Add the scope: https://www.googleapis.com/auth/gmail.modify")
                    print("7. Save and try again")
                    print("="*60 + "\n")
                raise
            with open(token_path, "w") as token:
                token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def list_messages(service, user_id="me", max_results=10, query=""):
    """
    List messages from Gmail inbox.
    
    Args:
        service: Gmail service object
        user_id: User's email address or 'me' for authenticated user
        max_results: Maximum number of messages to return (default: 10)
        query: Gmail search query (e.g., "from:example@gmail.com", "subject:test")
    
    Returns:
        List of message objects
    """
    try:
        results = (
            service.users()
            .messages()
            .list(userId=user_id, maxResults=max_results, q=query)
            .execute()
        )
        messages = results.get("messages", [])
        return messages
    except HttpError as error:
        print(f"An error occurred: {error}")
        return []


def get_message(service, message_id, user_id="me"):
    """
    Get a specific message by ID.
    
    Args:
        service: Gmail service object
        message_id: ID of the message to retrieve
        user_id: User's email address or 'me' for authenticated user
    
    Returns:
        Message object with full details
    """
    try:
        message = (
            service.users()
            .messages()
            .get(userId=user_id, id=message_id)
            .execute()
        )
        return message
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


def get_message_content(message):
    """
    Extract readable content from a Gmail message.
    
    Args:
        message: Message object from Gmail API
    
    Returns:
        Dictionary with subject, from, to, date, and body
    """
    payload = message.get("payload", {})
    headers = payload.get("headers", [])
    
    subject = next((h["value"] for h in headers if h["name"] == "Subject"), "")
    from_email = next((h["value"] for h in headers if h["name"] == "From"), "")
    to_email = next((h["value"] for h in headers if h["name"] == "To"), "")
    date = next((h["value"] for h in headers if h["name"] == "Date"), "")
    
    body = ""
    if "parts" in payload:
        for part in payload["parts"]:
            if part["mimeType"] == "text/plain":
                data = part["body"].get("data")
                if data:
                    body = base64.urlsafe_b64decode(data).decode("utf-8")
                    break
            elif part["mimeType"] == "text/html":
                data = part["body"].get("data")
                if data:
                    body = base64.urlsafe_b64decode(data).decode("utf-8")
    else:
        if payload.get("mimeType") == "text/plain":
            data = payload["body"].get("data")
            if data:
                body = base64.urlsafe_b64decode(data).decode("utf-8")
    
    return {
        "id": message.get("id"),
        "subject": subject,
        "from": from_email,
        "to": to_email,
        "date": date,
        "body": body,
        "snippet": message.get("snippet", ""),
    }


def send_email(service, to, subject, body, user_id="me", is_html=False):
    """
    Send an email via Gmail.
    
    Args:
        service: Gmail service object
        to: Recipient email address
        subject: Email subject
        body: Email body content
        user_id: User's email address or 'me' for authenticated user
        is_html: Whether the body is HTML (default: False)
    
    Returns:
        Sent message object
    """
    try:
        message = MIMEText(body, "html" if is_html else "plain")
        message["to"] = to
        message["subject"] = subject
        
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        
        send_message = (
            service.users()
            .messages()
            .send(userId=user_id, body={"raw": raw_message})
            .execute()
        )
        return send_message
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


def send_email_with_attachment(service, to, subject, body, attachment_path, user_id="me", is_html=False):
    """
    Send an email with attachment via Gmail.
    
    Args:
        service: Gmail service object
        to: Recipient email address
        subject: Email subject
        body: Email body content
        attachment_path: Path to attachment file
        user_id: User's email address or 'me' for authenticated user
        is_html: Whether the body is HTML (default: False)
    
    Returns:
        Sent message object
    """
    try:
        message = MIMEMultipart()
        message["to"] = to
        message["subject"] = subject
        
        msg_body = MIMEText(body, "html" if is_html else "plain")
        message.attach(msg_body)
        
        if os.path.exists(attachment_path):
            with open(attachment_path, "rb") as f:
                attachment = MIMEText(f.read(), "base64")
                attachment.add_header(
                    "Content-Disposition",
                    f'attachment; filename="{os.path.basename(attachment_path)}"',
                )
                message.attach(attachment)
        
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        
        send_message = (
            service.users()
            .messages()
            .send(userId=user_id, body={"raw": raw_message})
            .execute()
        )
        return send_message
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


def delete_message(service, message_id, user_id="me"):
    """
    Delete a message by ID.
    
    Args:
        service: Gmail service object
        message_id: ID of the message to delete
        user_id: User's email address or 'me' for authenticated user
    
    Returns:
        True if successful, False otherwise
    """
    try:
        service.users().messages().delete(userId=user_id, id=message_id).execute()
        return True
    except HttpError as error:
        print(f"An error occurred: {error}")
        return False


def mark_as_read(service, message_id, user_id="me"):
    """
    Mark a message as read.
    
    Args:
        service: Gmail service object
        message_id: ID of the message to mark as read
        user_id: User's email address or 'me' for authenticated user
    
    Returns:
        Updated message object
    """
    try:
        message = (
            service.users()
            .messages()
            .modify(
                userId=user_id,
                id=message_id,
                body={"removeLabelIds": ["UNREAD"]},
            )
            .execute()
        )
        return message
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


def mark_as_unread(service, message_id, user_id="me"):
    """
    Mark a message as unread.
    
    Args:
        service: Gmail service object
        message_id: ID of the message to mark as unread
        user_id: User's email address or 'me' for authenticated user
    
    Returns:
        Updated message object
    """
    try:
        message = (
            service.users()
            .messages()
            .modify(
                userId=user_id,
                id=message_id,
                body={"addLabelIds": ["UNREAD"]},
            )
            .execute()
        )
        return message
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


def main():
    """Example usage of Gmail functions."""
    try:
        service = get_service()

        # 1. List messages
        messages = list_messages(service, max_results=5)
        print(f"Found {len(messages)} messages")

        # 2. Get and display a message
        if messages:
            message = get_message(service, messages[0]["id"])
            if message:
                content = get_message_content(message)
                print(json.dumps(content, indent=2))

        # 3. Send a test email (uncomment to test)
        # send_email(service, "recipient@example.com", "Test Subject", "Test body")

    except HttpError as error:
        print("An error occurred:", error)


if __name__ == "__main__":
    main()

