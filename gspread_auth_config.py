import gspread
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


# Exemple d'ús:
# gspread_auth = get_gspread_auth("credencials.json")
