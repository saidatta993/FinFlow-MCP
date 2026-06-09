from db import get_recent_expenses, get_category_summary

def main():
    print("=== Recent Expenses ===")
    expenses = get_recent_expenses(limit=50)
    
    if not expenses:
        print("No expenses found.")
    else:
        for exp in expenses:
            print(f"[{exp['date']}] {exp['merchant']} - Rs. {exp['amount']:.2f} ({exp['category']})")

    print("\n=== Category Summary (All Time) ===")
    import sqlite3
    from db import get_connection
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT *
        FROM expenses
    ''')
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("No summary available.")
    else:
        for row in rows:
            print(f"{row['id'], row['date'],row['amount'],row['merchant'],row['category']}")

if __name__ == "__main__":
    main()
