import os
from dotenv import load_dotenv
from gmail_client import get_gmail_service

load_dotenv()

def test_queries():
    service = get_gmail_service()
    
    queries = [
        "subject:HDFC subject:debited",
        "subject:HDFC",
        "from:hdfcbank.net"
    ]
    
    for q in queries:
        results = service.users().messages().list(userId='me', q=q, maxResults=5).execute()
        messages = results.get('messages', [])
        print(f"Query: '{q}' found {len(messages)} messages.")
        for msg in messages:
            msg_data = service.users().messages().get(userId='me', id=msg['id'], format='metadata', metadataHeaders=['Subject']).execute()
            headers = msg_data['payload'].get('headers', [])
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
            print(f"  - Subject: {subject}")
        print()

if __name__ == "__main__":
    test_queries()
