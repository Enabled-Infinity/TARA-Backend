import os
import json

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Google Docs API scope
SCOPES = ["https://www.googleapis.com/auth/documents", "https://www.googleapis.com/auth/drive.file"]


def get_service():
    """Authenticate and return Google Docs service."""
    creds = None
    token_path = os.path.join(os.path.dirname(__file__), "token_docs.json")
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

    return build("docs", "v1", credentials=creds)


def get_drive_service():
    """Authenticate and return Google Drive service."""
    creds = None
    token_path = os.path.join(os.path.dirname(__file__), "token_docs.json")
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

    return build("drive", "v3", credentials=creds)


def create_document(service, title="Untitled Document"):
    """
    Create a new Google Doc.
    
    Args:
        service: Google Docs service object
        title: Title of the document
    
    Returns:
        Document object with ID and URL
    """
    try:
        document = {"title": title}
        doc = service.documents().create(body=document).execute()
        return {
            "id": doc.get("documentId"),
            "title": doc.get("title"),
            "url": f"https://docs.google.com/document/d/{doc.get('documentId')}/edit",
        }
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


def get_document(service, document_id):
    """
    Get a document by ID.
    
    Args:
        service: Google Docs service object
        document_id: ID of the document to retrieve
    
    Returns:
        Document object with full content
    """
    try:
        doc = service.documents().get(documentId=document_id).execute()
        return doc
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


def get_document_content(doc):
    """
    Extract readable text content from a Google Doc.
    
    Args:
        doc: Document object from Google Docs API
    
    Returns:
        Dictionary with title and text content
    """
    title = doc.get("title", "")
    content = doc.get("body", {}).get("content", [])
    
    text_content = []
    
    def extract_text(element):
        if "paragraph" in element:
            para = element["paragraph"]
            if "elements" in para:
                for elem in para["elements"]:
                    if "textRun" in elem:
                        text_content.append(elem["textRun"].get("content", ""))
        elif "table" in element:
            table = element["table"]
            if "tableRows" in table:
                for row in table["tableRows"]:
                    if "tableCells" in row:
                        for cell in row["tableCells"]:
                            if "content" in cell:
                                for cell_elem in cell["content"]:
                                    extract_text(cell_elem)
    
    for element in content:
        extract_text(element)
    
    return {
        "id": doc.get("documentId"),
        "title": title,
        "content": "".join(text_content),
    }


def insert_text(service, document_id, text, index=1):
    """
    Insert text into a document at a specific index.
    
    Args:
        service: Google Docs service object
        document_id: ID of the document
        text: Text to insert
        index: Character index where to insert (default: 1, which is after the document start)
    
    Returns:
        Updated document object
    """
    try:
        requests = [
            {
                "insertText": {
                    "location": {"index": index},
                    "text": text,
                }
            }
        ]
        result = service.documents().batchUpdate(documentId=document_id, body={"requests": requests}).execute()
        return result
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


def replace_text(service, document_id, search_text, replace_text):
    """
    Replace text in a document.
    
    Args:
        service: Google Docs service object
        document_id: ID of the document
        search_text: Text to search for
        replace_text: Text to replace with
    
    Returns:
        Updated document object
    """
    try:
        requests = [
            {
                "replaceAllText": {
                    "containsText": {"text": search_text, "matchCase": False},
                    "replaceText": replace_text,
                }
            }
        ]
        result = service.documents().batchUpdate(documentId=document_id, body={"requests": requests}).execute()
        return result
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


def delete_text(service, document_id, start_index, end_index):
    """
    Delete text from a document.
    
    Args:
        service: Google Docs service object
        document_id: ID of the document
        start_index: Start character index
        end_index: End character index
    
    Returns:
        Updated document object
    """
    try:
        requests = [
            {
                "deleteContentRange": {
                    "range": {
                        "startIndex": start_index,
                        "endIndex": end_index,
                    }
                }
            }
        ]
        result = service.documents().batchUpdate(documentId=document_id, body={"requests": requests}).execute()
        return result
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


def format_text(service, document_id, start_index, end_index, bold=None, italic=None, underline=None, font_size=None):
    """
    Format text in a document.
    
    Args:
        service: Google Docs service object
        document_id: ID of the document
        start_index: Start character index
        end_index: End character index
        bold: Whether to make text bold
        italic: Whether to make text italic
        underline: Whether to underline text
        font_size: Font size in points
    
    Returns:
        Updated document object
    """
    try:
        text_style = {}
        if bold is not None:
            text_style["bold"] = bold
        if italic is not None:
            text_style["italic"] = italic
        if underline is not None:
            text_style["underline"] = underline
        
        format_requests = {
            "range": {
                "startIndex": start_index,
                "endIndex": end_index,
            },
        }
        
        if text_style:
            format_requests["textStyle"] = text_style
        
        if font_size:
            if "textStyle" not in format_requests:
                format_requests["textStyle"] = {}
            format_requests["textStyle"]["fontSize"] = {"magnitude": font_size, "unit": "PT"}
        
        requests = [{"updateTextStyle": format_requests}]
        result = service.documents().batchUpdate(documentId=document_id, body={"requests": requests}).execute()
        return result
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


def list_documents(drive_service, max_results=10):
    """
    List Google Docs documents.
    
    Args:
        drive_service: Google Drive service object
        max_results: Maximum number of documents to return
    
    Returns:
        List of document objects
    """
    try:
        results = (
            drive_service.files()
            .list(
                q="mimeType='application/vnd.google-apps.document'",
                pageSize=max_results,
                fields="files(id, name, createdTime, modifiedTime, webViewLink)",
            )
            .execute()
        )
        files = results.get("files", [])
        return files
    except HttpError as error:
        print(f"An error occurred: {error}")
        return []


def delete_document(drive_service, document_id):
    """
    Delete a document by ID.
    
    Args:
        drive_service: Google Drive service object
        document_id: ID of the document to delete
    
    Returns:
        True if successful, False otherwise
    """
    try:
        drive_service.files().delete(fileId=document_id).execute()
        return True
    except HttpError as error:
        print(f"An error occurred: {error}")
        return False


def share_document(drive_service, document_id, email, role="reader"):
    """
    Share a document with a user.
    
    Args:
        drive_service: Google Drive service object
        document_id: ID of the document
        email: Email address of the user to share with
        role: Permission role ('reader', 'writer', 'commenter')
    
    Returns:
        Permission object
    """
    try:
        permission = {
            "type": "user",
            "role": role,
            "emailAddress": email,
        }
        result = drive_service.permissions().create(fileId=document_id, body=permission).execute()
        return result
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


def main():
    """Example usage of Google Docs functions."""
    try:
        service = get_service()
        drive_service = get_drive_service()

        # 1. Create a new document
        doc = create_document(service, "Test Document")
        if doc:
            print(f"Created document: {json.dumps(doc, indent=2)}")

        # 2. Insert text
        if doc:
            insert_text(service, doc["id"], "Hello, World!\nThis is a test document.")
            print("Inserted text")

        # 3. Get document content
        if doc:
            document = get_document(service, doc["id"])
            if document:
                content = get_document_content(document)
                print(f"Document content: {json.dumps(content, indent=2)}")

        # 4. List documents
        documents = list_documents(drive_service, max_results=5)
        print(f"Found {len(documents)} documents")

    except HttpError as error:
        print("An error occurred:", error)


if __name__ == "__main__":
    main()

