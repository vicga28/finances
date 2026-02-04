import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

def get_gspread_auth(credentials_dict_or_path):
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    if isinstance(credentials_dict_or_path, dict):
        credentials = Credentials.from_service_account_info(credentials_dict_or_path, scopes=scope)
    else:
        credentials = Credentials.from_service_account_file(credentials_dict_or_path, scopes=scope)

    return gspread.authorize(credentials)

#Autentificacio per l'API de Google Sheets
def authenticate_gspread(credentials_path_or_dict):
    """
    Authenticate with Google Sheets using the provided service account credentials.

    This function uses OAuth2 to authenticate with Google Sheets and
    provides access to spreadsheets, drive files, etc. depending on the scopes provided.

    Parameters:
    - credentials_path_or_dict (str/dict): The file path to the service account's JSON key
                                          or the actual credentials as a dictionary.

    Returns:
    - gspread.Client: An authenticated gspread client that can be used to interact with Google Sheets.

    Usage:
    >>> client = authenticate_gspread('path_to_service_account.json')
    or
    >>> creds_dict = {
    ...    'type': '...',
    ...    'project_id': '...',
    ...    # ... other credentials data
    ... }
    >>> client = authenticate_gspread(creds_dict)
    >>> sheet = client.open('My Spreadsheet')
    """
    # Define the scopes necessary for accessing and manipulating Google Sheets and Drive
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/drive"
    ]

    # Check the type of the provided credentials_path_or_dict to decide the method to use
    if isinstance(credentials_path_or_dict, str):
        creds = Credentials.from_service_account_info(credentials_path_or_dict, scope)
    elif isinstance(credentials_path_or_dict, dict):
        creds = Credentials.from_service_account_info(credentials_path_or_dict, scope)
    else:
        raise ValueError("The provided credentials_path_or_dict should be either a string (file path) or a dictionary (actual credentials).")

    # Authorize and return a gspread client
    client = gspread.authorize(creds)
    print("Successfully authenticated with Google Sheets.")
    return client

def fetch_data_from_sheet(client, spreadsheet_id, worksheet_name='DATA'):
    """
    Fetch data from a specific worksheet in a Google Sheet and return it as a list of lists.

    This function connects to a Google Sheet using the provided client and fetches data from a specified worksheet. 
    By default, it fetches data from the 'Revenue 2023' worksheet.

    Parameters:
    - client (gspread.Client): The client object that represents the Google Sheets API. Must be authenticated before calling this function.
    - spreadsheet_id (str): The unique identifier for the target Google Sheet. It is usually found in the sheet's URL.
    - worksheet_name (str, optional): The name of the worksheet to fetch data from. Defaults to 'Revenue 2023'.

    Returns:
    - list of lists: Rows of data fetched from the specified worksheet, where each row is represented as a list.

    Example:
    ```
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials

    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets",
             "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]

    creds = ServiceAccountCredentials.from_json_keyfile_name('your_credentials_file.json', scope)
    client = gspread.authorize(creds)

    spreadsheet_id = 'your_spreadsheet_id'
    data = fetch_data_from_sheet(client, spreadsheet_id, 'Some Worksheet Name')
    for row in data[:5]:  # print first five rows
        print(row)
    ```

    Note:
    Ensure the Google Sheet and the specified worksheet are accessible by the provided client credentials.
    """
    sheet = client.open_by_key(key=spreadsheet_id)
    data = sheet.worksheet(worksheet_name).get_values(value_render_option = "UNFORMATTED_VALUE")
    
    return data

def load_data(credentials, spreadsheet_id, sheet_name):
    client = authenticate_gspread(credentials)
    data = fetch_data_from_sheet(client, spreadsheet_id, worksheet_name=sheet_name)
    df = pd.DataFrame(data[1:], columns=data[0])
    return df



