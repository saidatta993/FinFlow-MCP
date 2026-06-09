import sys
import codecs
sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)

import os
import base64
from dotenv import load_dotenv
from gmail_client import get_gmail_service

load_dotenv()

def fetch_body():
    service = get_gmail_service()
    
    query = 'subject:"Account update for your HDFC Bank A/c"'
    results = service.users().messages().list(userId='me', q=query, maxResults=2).execute()
    messages = results.get('messages', [])
    
    for msg in messages:
        msg_data = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
        payload = msg_data.get('payload', {})
        
        body = ""
        if 'parts' in payload:
            for part in payload['parts']:
                if part.get('mimeType') == 'text/plain':
                    data = part.get('body', {}).get('data', '')
                    if data:
                        body = base64.urlsafe_b64decode(data).decode('utf-8')
                        break
        else:
            data = payload.get('body', {}).get('data', '')
            if data:
                body = base64.urlsafe_b64decode(data).decode('utf-8')
                
        print("BODY START:")
        print(body)
        print("BODY END.\n")

if __name__ == "__main__":
    fetch_body()
