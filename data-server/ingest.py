import csv
import os
from dotenv import load_dotenv
from gmail_client import fetch_hdfc_alert_emails
from parser import parse_hdfc_alert
from db import init_db, insert_expense

load_dotenv()
CATEGORIES_CSV = os.getenv("CATEGORIES_CSV", "./categories.csv")

def load_categories() -> dict[str, str]:
    """Loads merchant keyword to category mapping from CSV."""
    mapping = {}
    if not os.path.exists(CATEGORIES_CSV):
        return mapping
        
    with open(CATEGORIES_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            mapping[row['merchant_keyword'].lower()] = row['category']
    return mapping

def determine_category(merchant: str, mapping: dict[str, str]) -> str:
    """Finds the best category match for a merchant based on keywords."""
    merchant_lower = merchant.lower()
    for keyword, category in mapping.items():
        if keyword in merchant_lower:
            return category
    return "Uncategorized"

def main():
    print("Initializing database...")
    init_db()
    
    print("Loading categories...")
    categories_map = load_categories()
    
    print("Fetching HDFC alert emails...")
    try:
        emails = fetch_hdfc_alert_emails(max_results=400)
    except Exception as e:
        print(f"Failed to fetch emails: {e}")
        return

    print(f"Found {len(emails)} potential alert emails.")
    
    ingested = 0
    skipped = 0
    
    for email_body in emails:
        parsed = parse_hdfc_alert(email_body)
        if parsed:
            category = determine_category(parsed['merchant'], categories_map)
            insert_expense(
                date=parsed['date'],
                amount=parsed['amount'],
                merchant=parsed['merchant'],
                category=category,
                exp_type=parsed['type']
            )
            ingested += 1
        else:
            skipped += 1
            
    print(f"\nSummary: Ingested {ingested} expenses, skipped {skipped} unparseable emails.")

if __name__ == "__main__":
    main()
