import openpyxl

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets'
]

def get_google_services():
    creds = service_account.Credentials.from_service_account_file(
        '/opt/odoo17/google_service_account.json',
        scopes=SCOPES
    )

    drive_service = build('drive', 'v3', credentials=creds)
    sheets_service = build('sheets', 'v4', credentials=creds)

    return drive_service, sheets_service

def preview_exel_file(file):
    self.ensure_one()
    wb = openpyxl.load_workbook(io.BytesIO(file))
    sheet = wb.active
    values = [[cell for cell in row] for row in sheet.iter_rows(values_only=True)]
    drive_service, sheet_service = get_google_services()

    sheet_service.spreadsheets().values().update(
        spreadsheetId="1v1WjEiAY7CrgnCiG0IAZEdONxqJUo8CPZHTqyt_pYmw",
        range='Sheet1!A1',
        valueInputOption='USER_ENTERED',
        body={'values': values}
    ).execute()

    google_sheet_url = (
        f"https://docs.google.com/spreadsheets/d/1v1WjEiAY7CrgnCiG0IAZEdONxqJUo8CPZHTqyt_pYmw/edit?gid=0#gid=0"
    )
    return {
        'type': 'ir.actions.act_url',
        'url': google_sheet_url,
        'target': 'new',
    }