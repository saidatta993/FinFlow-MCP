import re
from datetime import datetime

def parse_hdfc_alert(text: str) -> dict | None:
    """
    Parses HDFC SMS/Email debit alert text and extracts amount, merchant, and date.
    Returns a dictionary or None if parsing fails.
    """
    # Replace newlines with spaces to handle multiline alerts
    text = text.replace('\n', ' ').replace('\r', ' ')
    
    # Format 1: Rs.1,250.00 debited from a/c **1234 on 04-06-25 to VPA merchant@upi.
    # Group 1: Amount (e.g., 1,250.00)
    # Group 2: Date (e.g., 04-06-25)
    # Group 3: Merchant/VPA (e.g., merchant@upi)
    pattern1 = r"Rs\.([\d,]+\.\d{2})\s+debited.*?on\s+(\d{2}-\d{2}-\d{2})\s+to\s+VPA\s+(.*?)\."
    
    # Format 2: Your A/c **1234 has been debited with INR 500.00 on 05-JUN-2025 at SWIGGY INDIA.
    # Group 1: Amount (e.g., 500.00)
    # Group 2: Date (e.g., 05-JUN-2025)
    # Group 3: Merchant (e.g., SWIGGY INDIA)
    pattern2 = r"debited with INR\s+([\d,]+\.\d{2})\s+on\s+(\d{2}-[a-zA-Z]{3}-\d{4})\s+at\s+(.*?)\."

    # Format 3: Rs.60.00 is debited from your account ending 3872 towards VPA merchant on 07-06-26.
    # Group 1: Amount (e.g., 60.00)
    # Group 2: Merchant (e.g., merchant)
    # Group 3: Date (e.g., 07-06-26)
    pattern3 = r"Rs\.([\d,]+\.\d{2})\s+(?:is|has\s+been)\s+debited\s+from.*?to(?:wards)?\s+(?:VPA\s+)?(.*?)\s+on\s+(\d{2}-\d{2}-\d{2})"
    
    match = re.search(pattern1, text, re.IGNORECASE)
    if match:
        amount_str, date_str, merchant = match.groups()
        # Parse date DD-MM-YY to ISO YYYY-MM-DD
        date_obj = datetime.strptime(date_str, "%d-%m-%y")
    else:
        match = re.search(pattern2, text, re.IGNORECASE)
        if match:
            amount_str, date_str, merchant = match.groups()
            # Parse date DD-MMM-YYYY to ISO YYYY-MM-DD
            date_obj = datetime.strptime(date_str.upper(), "%d-%b-%Y")
        else:
            match = re.search(pattern3, text, re.IGNORECASE)
            if match:
                amount_str, merchant, date_str = match.groups()
                # Parse date DD-MM-YY to ISO YYYY-MM-DD
                date_obj = datetime.strptime(date_str, "%d-%m-%y")
            else:
                return None
            
    # Clean up amount (remove commas and convert to float)
    amount = float(amount_str.replace(',', ''))
    
    # Clean up merchant (remove @upi, trailing spaces, etc.)
    merchant = merchant.strip()
    if merchant.lower().endswith('@upi'):
        merchant = merchant[:-4]
    
    return {
        "amount": amount,
        "merchant": merchant,
        "date": date_obj.strftime("%Y-%m-%d"),
        "type": "debit"
    }
