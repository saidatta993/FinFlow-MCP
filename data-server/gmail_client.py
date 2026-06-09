import os
import base64
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

load_dotenv()

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
CREDENTIALS_PATH = os.getenv("GMAIL_CREDENTIALS_JSON", "./credentials.json")
TOKEN_PATH = os.getenv("GMAIL_TOKEN_JSON", "./token.json")

def get_gmail_service():
    """Authenticates and returns a Gmail API service object. Uses stored token, refreshes if expired."""
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_PATH):
                raise FileNotFoundError(f"Missing {CREDENTIALS_PATH}. Please provide OAuth credentials from Google Cloud Console.")
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
            
        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)

def fetch_hdfc_alert_emails(max_results: int = 50) -> list[str]:
    """Searches inbox for emails where subject contains 'HDFC' and 'debited', returns list of plain text email bodies."""
    service = get_gmail_service()
    
    query = "HDFC debited"
    results = service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
    messages = results.get('messages', [])
    
    bodies = []
    if not messages:
        return bodies
        
    for msg in messages:
        msg_data = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
        payload = msg_data.get('payload', {})
        
        # Extract body (handling different mime types)
        body = ""
        if 'parts' in payload:
            # Try to get text/plain first
            for part in payload['parts']:
                if part.get('mimeType') == 'text/plain':
                    data = part.get('body', {}).get('data', '')
                    if data:
                        body = base64.urlsafe_b64decode(data).decode('utf-8')
                        break
            # Fallback to text/html
            if not body:
                for part in payload['parts']:
                    if part.get('mimeType') == 'text/html':
                        data = part.get('body', {}).get('data', '')
                        if data:
                            raw_html = base64.urlsafe_b64decode(data).decode('utf-8')
                            import re
                            import html
                            text = re.sub(r'<style.*?>.*?</style>', '', raw_html, flags=re.IGNORECASE|re.DOTALL)
                            text = re.sub(r'<script.*?>.*?</script>', '', text, flags=re.IGNORECASE|re.DOTALL)
                            text = re.sub(r'<[^>]+>', ' ', text)
                            text = html.unescape(text)
                            body = re.sub(r'\s+', ' ', text).strip()
                            break
        else:
            data = payload.get('body', {}).get('data', '')
            if data:
                body = base64.urlsafe_b64decode(data).decode('utf-8')
                
        # Final fallback to snippet if body is still empty
        if not body:
            body = msg_data.get('snippet', '')
                
        if body:
            bodies.append(body)
            
    return bodies
