import os
import json
import io
from mimetypes import guess_type

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload, MediaIoBaseUpload
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Google Drive API scope
SCOPES = ["https://www.googleapis.com/auth/drive"]


def get_service():
    """Authenticate and return Google Drive service."""
    creds = None
    token_path = os.path.join(os.path.dirname(__file__), "token_drive.json")
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


def list_files(service, page_size=10, query="", fields="files(id, name, mimeType, size, createdTime, modifiedTime, webViewLink)"):
    """
    List files in Google Drive.
    
    Args:
        service: Google Drive service object
        page_size: Maximum number of files to return (default: 10)
        query: Search query (e.g., "name contains 'test'", "mimeType='application/pdf'")
        fields: Fields to return (default: basic file info)
    
    Returns:
        List of file objects
    """
    try:
        results = (
            service.files()
            .list(pageSize=page_size, q=query, fields=f"nextPageToken, {fields}")
            .execute()
        )
        files = results.get("files", [])
        return files
    except HttpError as error:
        print(f"An error occurred: {error}")
        return []


def get_file(service, file_id, fields="id, name, mimeType, size, createdTime, modifiedTime, webViewLink, parents"):
    """
    Get file metadata by ID.
    
    Args:
        service: Google Drive service object
        file_id: ID of the file to retrieve
        fields: Fields to return
    
    Returns:
        File object with metadata
    """
    try:
        file = service.files().get(fileId=file_id, fields=fields).execute()
        return file
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


def upload_file(service, file_path, name=None, mime_type=None, parent_folder_id=None):
    """
    Upload a file to Google Drive.
    
    Args:
        service: Google Drive service object
        file_path: Path to the file to upload
        name: Name for the file in Drive (default: original filename)
        mime_type: MIME type of the file (default: guessed from extension)
        parent_folder_id: ID of parent folder (optional)
    
    Returns:
        Uploaded file object
    """
    try:
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return None
        
        if name is None:
            name = os.path.basename(file_path)
        
        if mime_type is None:
            mime_type, _ = guess_type(file_path)
            if mime_type is None:
                mime_type = "application/octet-stream"
        
        file_metadata = {"name": name}
        if parent_folder_id:
            file_metadata["parents"] = [parent_folder_id]
        
        media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)
        
        file = (
            service.files()
            .create(body=file_metadata, media_body=media, fields="id, name, mimeType, size, webViewLink")
            .execute()
        )
        return file
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


def upload_file_content(service, content, name, mime_type="text/plain", parent_folder_id=None):
    """
    Upload file content (string or bytes) to Google Drive.
    
    Args:
        service: Google Drive service object
        content: File content (string or bytes)
        name: Name for the file in Drive
        mime_type: MIME type of the file (default: 'text/plain')
        parent_folder_id: ID of parent folder (optional)
    
    Returns:
        Uploaded file object
    """
    try:
        file_metadata = {"name": name}
        if parent_folder_id:
            file_metadata["parents"] = [parent_folder_id]
        
        if isinstance(content, str):
            content = content.encode("utf-8")
        
        media = MediaIoBaseUpload(io.BytesIO(content), mimetype=mime_type, resumable=True)
        
        file = (
            service.files()
            .create(body=file_metadata, media_body=media, fields="id, name, mimeType, size, webViewLink")
            .execute()
        )
        return file
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


def download_file(service, file_id, download_path=None):
    """
    Download a file from Google Drive.
    
    Args:
        service: Google Drive service object
        file_id: ID of the file to download
        download_path: Path to save the file (default: current directory with original name)
    
    Returns:
        Path to downloaded file, or None if error
    """
    try:
        file_metadata = get_file(service, file_id, fields="id, name, mimeType")
        if not file_metadata:
            return None
        
        # Check if it's a Google Workspace file (Docs, Sheets, etc.)
        mime_type = file_metadata.get("mimeType", "")
        if mime_type.startswith("application/vnd.google-apps"):
            # Export as PDF or other format
            request = service.files().export_media(fileId=file_id, mimeType="application/pdf")
            if download_path is None:
                download_path = file_metadata.get("name", "download") + ".pdf"
        else:
            # Regular file download
            request = service.files().get_media(fileId=file_id)
            if download_path is None:
                download_path = file_metadata.get("name", "download")
        
        with open(download_path, "wb") as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
        
        return download_path
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


def download_file_content(service, file_id):
    """
    Download file content as bytes.
    
    Args:
        service: Google Drive service object
        file_id: ID of the file to download
    
    Returns:
        File content as bytes, or None if error
    """
    try:
        file_metadata = get_file(service, file_id, fields="id, name, mimeType")
        if not file_metadata:
            return None
        
        mime_type = file_metadata.get("mimeType", "")
        if mime_type.startswith("application/vnd.google-apps"):
            request = service.files().export_media(fileId=file_id, mimeType="text/plain")
        else:
            request = service.files().get_media(fileId=file_id)
        
        content = io.BytesIO()
        downloader = MediaIoBaseDownload(content, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        
        return content.getvalue()
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


def create_folder(service, name, parent_folder_id=None):
    """
    Create a folder in Google Drive.
    
    Args:
        service: Google Drive service object
        name: Name of the folder
        parent_folder_id: ID of parent folder (optional)
    
    Returns:
        Created folder object
    """
    try:
        file_metadata = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        if parent_folder_id:
            file_metadata["parents"] = [parent_folder_id]
        
        folder = (
            service.files()
            .create(body=file_metadata, fields="id, name, mimeType, webViewLink")
            .execute()
        )
        return folder
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


def update_file(service, file_id, name=None, description=None, add_parents=None, remove_parents=None):
    """
    Update file metadata.
    
    Args:
        service: Google Drive service object
        file_id: ID of the file to update
        name: New name for the file (optional)
        description: New description (optional)
        add_parents: List of parent folder IDs to add (optional)
        remove_parents: List of parent folder IDs to remove (optional)
    
    Returns:
        Updated file object
    """
    try:
        file_metadata = {}
        if name:
            file_metadata["name"] = name
        if description is not None:
            file_metadata["description"] = description
        
        update_params = {"fileId": file_id, "body": file_metadata}
        if add_parents:
            update_params["addParents"] = ",".join(add_parents)
        if remove_parents:
            update_params["removeParents"] = ",".join(remove_parents)
        
        file = service.files().update(**update_params, fields="id, name, mimeType, webViewLink").execute()
        return file
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


def delete_file(service, file_id):
    """
    Delete a file or folder by ID.
    
    Args:
        service: Google Drive service object
        file_id: ID of the file/folder to delete
    
    Returns:
        True if successful, False otherwise
    """
    try:
        service.files().delete(fileId=file_id).execute()
        return True
    except HttpError as error:
        print(f"An error occurred: {error}")
        return False


def share_file(service, file_id, email, role="reader", notify=True):
    """
    Share a file with a user.
    
    Args:
        service: Google Drive service object
        file_id: ID of the file to share
        email: Email address of the user to share with
        role: Permission role ('reader', 'writer', 'commenter', 'owner')
        notify: Whether to send notification email (default: True)
    
    Returns:
        Permission object
    """
    try:
        permission = {
            "type": "user",
            "role": role,
            "emailAddress": email,
        }
        result = (
            service.permissions()
            .create(fileId=file_id, body=permission, sendNotificationEmail=notify)
            .execute()
        )
        return result
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


def share_file_public(service, file_id, role="reader"):
    """
    Share a file publicly (anyone with the link).
    
    Args:
        service: Google Drive service object
        file_id: ID of the file to share
        role: Permission role ('reader', 'writer', 'commenter')
    
    Returns:
        Permission object
    """
    try:
        permission = {
            "type": "anyone",
            "role": role,
        }
        result = service.permissions().create(fileId=file_id, body=permission).execute()
        return result
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


def get_file_permissions(service, file_id):
    """
    Get list of permissions for a file.
    
    Args:
        service: Google Drive service object
        file_id: ID of the file
    
    Returns:
        List of permission objects
    """
    try:
        result = service.permissions().list(fileId=file_id).execute()
        permissions = result.get("permissions", [])
        return permissions
    except HttpError as error:
        print(f"An error occurred: {error}")
        return []


def remove_permission(service, file_id, permission_id):
    """
    Remove a permission from a file.
    
    Args:
        service: Google Drive service object
        file_id: ID of the file
        permission_id: ID of the permission to remove
    
    Returns:
        True if successful, False otherwise
    """
    try:
        service.permissions().delete(fileId=file_id, permissionId=permission_id).execute()
        return True
    except HttpError as error:
        print(f"An error occurred: {error}")
        return False


def copy_file(service, file_id, name=None, parent_folder_id=None):
    """
    Copy a file.
    
    Args:
        service: Google Drive service object
        file_id: ID of the file to copy
        name: Name for the copied file (optional)
        parent_folder_id: ID of parent folder for the copy (optional)
    
    Returns:
        Copied file object
    """
    try:
        file_metadata = {}
        if name:
            file_metadata["name"] = name
        if parent_folder_id:
            file_metadata["parents"] = [parent_folder_id]
        
        copied_file = (
            service.files()
            .copy(fileId=file_id, body=file_metadata, fields="id, name, mimeType, webViewLink")
            .execute()
        )
        return copied_file
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


def search_files(service, query, page_size=10):
    """
    Search for files using a query.
    
    Args:
        service: Google Drive service object
        query: Search query (e.g., "name contains 'test'", "mimeType='application/pdf'")
        page_size: Maximum number of results (default: 10)
    
    Returns:
        List of matching file objects
    """
    return list_files(service, page_size=page_size, query=query)


def get_folders(service, page_size=10):
    """
    List all folders in Google Drive.
    
    Args:
        service: Google Drive service object
        page_size: Maximum number of folders to return (default: 10)
    
    Returns:
        List of folder objects
    """
    query = "mimeType='application/vnd.google-apps.folder'"
    return list_files(service, page_size=page_size, query=query)


def main():
    """Example usage of Google Drive functions."""
    try:
        service = get_service()

        # 1. List files
        files = list_files(service, page_size=5)
        print(f"Found {len(files)} files")

        # 2. Create a folder
        folder = create_folder(service, "Test Folder")
        if folder:
            print(f"Created folder: {json.dumps(folder, indent=2)}")

        # 3. Upload a file (uncomment to test)
        # uploaded = upload_file(service, "path/to/file.txt")
        # if uploaded:
        #     print(f"Uploaded file: {json.dumps(uploaded, indent=2)}")

        # 4. Search for files
        pdf_files = search_files(service, "mimeType='application/pdf'", page_size=5)
        print(f"Found {len(pdf_files)} PDF files")

    except HttpError as error:
        print("An error occurred:", error)


if __name__ == "__main__":
    main()

