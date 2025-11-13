import os
import json

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Google Sheets API scope
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def get_service():
    """Authenticate and return Google Sheets service."""
    creds = None
    token_path = os.path.join(os.path.  dirname(__file__), "token_sheets.json")
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

    return build("sheets", "v4", credentials=creds)


def create_spreadsheet(service, title="Untitled Spreadsheet"):
    """
    Create a new Google Spreadsheet.
    
    Args:
        service: Google Sheets service object
        title: Title of the spreadsheet
    
    Returns:
        Spreadsheet object with ID and URL
    """
    try:
        spreadsheet = {"properties": {"title": title}}
        spreadsheet = service.spreadsheets().create(body=spreadsheet, fields="spreadsheetId,spreadsheetUrl").execute()
        return {
            "id": spreadsheet.get("spreadsheetId"),
            "title": title,
            "url": spreadsheet.get("spreadsheetUrl"),
        }
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


def get_spreadsheet(service, spreadsheet_id, ranges=None, include_grid_data=False):
    """
    Get spreadsheet metadata and optionally data.
    
    Args:
        service: Google Sheets service object
        spreadsheet_id: ID of the spreadsheet
        ranges: List of A1 notation ranges to retrieve (optional)
        include_grid_data: Whether to include cell data (default: False)
    
    Returns:
        Spreadsheet object
    """
    try:
        params = {"spreadsheetId": spreadsheet_id}
        if ranges:
            params["ranges"] = ranges
        if include_grid_data:
            params["includeGridData"] = True
        
        spreadsheet = service.spreadsheets().get(**params).execute()
        return spreadsheet
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


def read_range(service, spreadsheet_id, range_name):
    """
    Read data from a specific range.
    
    Args:
        service: Google Sheets service object
        spreadsheet_id: ID of the spreadsheet
        range_name: A1 notation range (e.g., 'Sheet1!A1:B10')
    
    Returns:
        List of rows (each row is a list of cell values)
    """
    try:
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=range_name)
            .execute()
        )
        values = result.get("values", [])
        return values
    except HttpError as error:
        print(f"An error occurred: {error}")
        return []


def write_range(service, spreadsheet_id, range_name, values, value_input_option="RAW"):
    """
    Write data to a specific range.
    
    Args:
        service: Google Sheets service object
        spreadsheet_id: ID of the spreadsheet
        range_name: A1 notation range (e.g., 'Sheet1!A1:B10')
        values: List of rows (each row is a list of cell values)
        value_input_option: How to interpret input ('RAW' or 'USER_ENTERED')
    
    Returns:
        Update response object
    """
    try:
        body = {"values": values}
        result = (
            service.spreadsheets()
            .values()
            .update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption=value_input_option,
                body=body,
            )
            .execute()
        )
        return result
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


def append_row(service, spreadsheet_id, range_name, values, value_input_option="RAW"):
    """
    Append a row to the end of a range.
    
    Args:
        service: Google Sheets service object
        spreadsheet_id: ID of the spreadsheet
        range_name: A1 notation range (e.g., 'Sheet1!A1:B')
        values: List of cell values for the row
        value_input_option: How to interpret input ('RAW' or 'USER_ENTERED')
    
    Returns:
        Append response object
    """
    try:
        body = {"values": [values]}
        result = (
            service.spreadsheets()
            .values()
            .append(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption=value_input_option,
                body=body,
            )
            .execute()
        )
        return result
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


def clear_range(service, spreadsheet_id, range_name):
    """
    Clear data from a specific range.
    
    Args:
        service: Google Sheets service object
        spreadsheet_id: ID of the spreadsheet
        range_name: A1 notation range (e.g., 'Sheet1!A1:B10')
    
    Returns:
        Clear response object
    """
    try:
        result = (
            service.spreadsheets()
            .values()
            .clear(spreadsheetId=spreadsheet_id, range=range_name)
            .execute()
        )
        return result
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


def batch_update(service, spreadsheet_id, requests):
    """
    Perform batch updates on a spreadsheet.
    
    Args:
        service: Google Sheets service object
        spreadsheet_id: ID of the spreadsheet
        requests: List of request objects (see Google Sheets API docs)
    
    Returns:
        Batch update response object
    """
    try:
        body = {"requests": requests}
        result = service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()
        return result
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


def update_cell(service, spreadsheet_id, sheet_name, row, col, value, value_input_option="RAW"):
    """
    Update a single cell.
    
    Args:
        service: Google Sheets service object
        spreadsheet_id: ID of the spreadsheet
        sheet_name: Name of the sheet
        row: Row number (1-indexed)
        col: Column number (1-indexed) or letter (e.g., 'A')
        value: Value to set
        value_input_option: How to interpret input ('RAW' or 'USER_ENTERED')
    
    Returns:
        Update response object
    """
    try:
        # Convert column letter to number if needed
        if isinstance(col, str):
            col_num = ord(col.upper()) - ord("A") + 1
        else:
            col_num = col
        
        range_name = f"{sheet_name}!{chr(ord('A') + col_num - 1)}{row}"
        return write_range(service, spreadsheet_id, range_name, [[value]], value_input_option)
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


def get_cell(service, spreadsheet_id, sheet_name, row, col):
    """
    Get a single cell value.
    
    Args:
        service: Google Sheets service object
        spreadsheet_id: ID of the spreadsheet
        sheet_name: Name of the sheet
        row: Row number (1-indexed)
        col: Column number (1-indexed) or letter (e.g., 'A')
    
    Returns:
        Cell value, or None if error
    """
    try:
        # Convert column letter to number if needed
        if isinstance(col, str):
            col_num = ord(col.upper()) - ord("A") + 1
        else:
            col_num = col
        
        range_name = f"{sheet_name}!{chr(ord('A') + col_num - 1)}{row}"
        values = read_range(service, spreadsheet_id, range_name)
        if values and len(values) > 0 and len(values[0]) > 0:
            return values[0][0]
        return None
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


def add_sheet(service, spreadsheet_id, title):
    """
    Add a new sheet to the spreadsheet.
    
    Args:
        service: Google Sheets service object
        spreadsheet_id: ID of the spreadsheet
        title: Title of the new sheet
    
    Returns:
        Batch update response object
    """
    try:
        requests = [
            {
                "addSheet": {
                    "properties": {
                        "title": title,
                    }
                }
            }
        ]
        return batch_update(service, spreadsheet_id, requests)
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


def delete_sheet(service, spreadsheet_id, sheet_id):
    """
    Delete a sheet from the spreadsheet.
    
    Args:
        service: Google Sheets service object
        spreadsheet_id: ID of the spreadsheet
        sheet_id: ID of the sheet to delete
    
    Returns:
        Batch update response object
    """
    try:
        requests = [
            {
                "deleteSheet": {
                    "sheetId": sheet_id,
                }
            }
        ]
        return batch_update(service, spreadsheet_id, requests)
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


def format_cells(service, spreadsheet_id, sheet_id, start_row, end_row, start_col, end_col, **format_options):
    """
    Format a range of cells.
    
    Args:
        service: Google Sheets service object
        spreadsheet_id: ID of the spreadsheet
        sheet_id: ID of the sheet
        start_row: Start row (0-indexed)
        end_row: End row (0-indexed, exclusive)
        start_col: Start column (0-indexed)
        end_col: End column (0-indexed, exclusive)
        **format_options: Format options (backgroundColor, textFormat, etc.)
    
    Returns:
        Batch update response object
    """
    try:
        cell_data = {}
        
        if "backgroundColor" in format_options:
            cell_data["userEnteredFormat"] = {
                "backgroundColor": format_options["backgroundColor"]
            }
        
        if "textFormat" in format_options:
            if "userEnteredFormat" not in cell_data:
                cell_data["userEnteredFormat"] = {}
            cell_data["userEnteredFormat"]["textFormat"] = format_options["textFormat"]
        
        if "numberFormat" in format_options:
            if "userEnteredFormat" not in cell_data:
                cell_data["userEnteredFormat"] = {}
            cell_data["userEnteredFormat"]["numberFormat"] = format_options["numberFormat"]
        
        requests = [
            {
                "updateCells": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": start_row,
                        "endRowIndex": end_row,
                        "startColumnIndex": start_col,
                        "endColumnIndex": end_col,
                    },
                    "rows": [
                        {
                            "values": [
                                cell_data for _ in range(end_col - start_col)
                            ]
                        }
                        for _ in range(end_row - start_row)
                    ],
                    "fields": "userEnteredFormat",
                }
            }
        ]
        return batch_update(service, spreadsheet_id, requests)
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


def set_column_width(service, spreadsheet_id, sheet_id, start_col, end_col, width):
    """
    Set column width.
    
    Args:
        service: Google Sheets service object
        spreadsheet_id: ID of the spreadsheet
        sheet_id: ID of the sheet
        start_col: Start column index (0-indexed)
        end_col: End column index (0-indexed, exclusive)
        width: Width in pixels
    
    Returns:
        Batch update response object
    """
    try:
        requests = [
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": start_col,
                        "endIndex": end_col,
                    },
                    "properties": {
                        "pixelSize": width,
                    },
                    "fields": "pixelSize",
                }
            }
        ]
        return batch_update(service, spreadsheet_id, requests)
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


def set_row_height(service, spreadsheet_id, sheet_id, start_row, end_row, height):
    """
    Set row height.
    
    Args:
        service: Google Sheets service object
        spreadsheet_id: ID of the spreadsheet
        sheet_id: ID of the sheet
        start_row: Start row index (0-indexed)
        end_row: End row index (0-indexed, exclusive)
        height: Height in pixels
    
    Returns:
        Batch update response object
    """
    try:
        requests = [
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "ROWS",
                        "startIndex": start_row,
                        "endIndex": end_row,
                    },
                    "properties": {
                        "pixelSize": height,
                    },
                    "fields": "pixelSize",
                }
            }
        ]
        return batch_update(service, spreadsheet_id, requests)
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


def batch_read(service, spreadsheet_id, ranges):
    """
    Read multiple ranges in a single request.
    
    Args:
        service: Google Sheets service object
        spreadsheet_id: ID of the spreadsheet
        ranges: List of A1 notation ranges
    
    Returns:
        Dictionary mapping ranges to their values
    """
    try:
        result = (
            service.spreadsheets()
            .values()
            .batchGet(spreadsheetId=spreadsheet_id, ranges=ranges)
            .execute()
        )
        value_ranges = result.get("valueRanges", [])
        return {vr["range"]: vr.get("values", []) for vr in value_ranges}
    except HttpError as error:
        print(f"An error occurred: {error}")
        return {}


def batch_write(service, spreadsheet_id, data, value_input_option="RAW"):
    """
    Write to multiple ranges in a single request.
    
    Args:
        service: Google Sheets service object
        spreadsheet_id: ID of the spreadsheet
        data: List of dicts with 'range' and 'values' keys
        value_input_option: How to interpret input ('RAW' or 'USER_ENTERED')
    
    Returns:
        Batch update response object
    """
    try:
        body = {
            "valueInputOption": value_input_option,
            "data": data,
        }
        result = (
            service.spreadsheets()
            .values()
            .batchUpdate(spreadsheetId=spreadsheet_id, body=body)
            .execute()
        )
        return result
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


def get_sheet_info(service, spreadsheet_id):
    """
    Get information about all sheets in the spreadsheet.
    
    Args:
        service: Google Sheets service object
        spreadsheet_id: ID of the spreadsheet
    
    Returns:
        List of sheet objects with id, title, and properties
    """
    try:
        spreadsheet = get_spreadsheet(service, spreadsheet_id)
        if spreadsheet:
            sheets = spreadsheet.get("sheets", [])
            return [
                {
                    "id": sheet["properties"]["sheetId"],
                    "title": sheet["properties"]["title"],
                    "index": sheet["properties"]["index"],
                    "rowCount": sheet["properties"].get("gridProperties", {}).get("rowCount"),
                    "columnCount": sheet["properties"].get("gridProperties", {}).get("columnCount"),
                }
                for sheet in sheets
            ]
        return []
    except HttpError as error:
        print(f"An error occurred: {error}")
        return []


def main():
    """Example usage of Google Sheets functions."""
    try:
        service = get_service()

        # 1. Create a new spreadsheet
        spreadsheet = create_spreadsheet(service, "Test Spreadsheet")
        if spreadsheet:
            print(f"Created spreadsheet: {json.dumps(spreadsheet, indent=2)}")

        # 2. Write data
        if spreadsheet:
            values = [
                ["Name", "Age", "City"],
                ["Alice", "30", "New York"],
                ["Bob", "25", "San Francisco"],
            ]
            write_range(service, spreadsheet["id"], "Sheet1!A1:C3", values)
            print("Wrote data to spreadsheet")

        # 3. Read data
        if spreadsheet:
            data = read_range(service, spreadsheet["id"], "Sheet1!A1:C3")
            print(f"Read data: {json.dumps(data, indent=2)}")

        # 4. Get sheet info
        if spreadsheet:
            sheets = get_sheet_info(service, spreadsheet["id"])
            print(f"Sheet info: {json.dumps(sheets, indent=2)}")

    except HttpError as error:
        print("An error occurred:", error)


if __name__ == "__main__":
    main()

