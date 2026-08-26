from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES=["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive.metadata.readonly"]
class GoogleSheetsClient:
    def __init__(self, token: dict): self.credentials=Credentials.from_authorized_user_info(token,SCOPES); self.service=build("sheets","v4",credentials=self.credentials,cache_discovery=False)
    def metadata(self, spreadsheet_id): return self.service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    def rows(self, spreadsheet_id, worksheet): return self.service.spreadsheets().values().get(spreadsheetId=spreadsheet_id,range=f"'{worksheet}'").execute().get("values",[])
    def write_rows(self, spreadsheet_id, worksheet, rows): return self.service.spreadsheets().values().update(spreadsheetId=spreadsheet_id,range=f"'{worksheet}'!A1",valueInputOption="USER_ENTERED",body={"values":rows}).execute()
    @staticmethod
    def normalize(rows, mapping):
        if not rows: return []
        headers=rows[0]; indices={field:headers.index(column) for column,field in mapping.items() if column in headers}
        return [{field:(row[i] if i<len(row) else None) for field,i in indices.items()} for row in rows[1:]]

