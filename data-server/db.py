import sqlite3
import os
from dotenv import load_dotenv

# Resolve paths relative to THIS FILE's directory (data-server/), not CWD.
# Critical: Claude Desktop spawns ui-server/main.py from an arbitrary CWD,
# so any relative path from .env (e.g. "./finance.db") would break.
# We always resolve relative paths against this file's own directory.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_THIS_DIR, ".env"))

_db_raw = os.getenv("DB_PATH", "finance.db")
# If the value from .env is relative (e.g. "./finance.db"), anchor it to _THIS_DIR
DB_PATH = _db_raw if os.path.isabs(_db_raw) else os.path.join(_THIS_DIR, _db_raw)

def get_connection():
    """Returns a SQLite connection to the database, ensuring dict factory is used."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Creates the expenses table if it does not exist."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS expenses (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        date      TEXT NOT NULL,
        amount    REAL NOT NULL,
        merchant  TEXT NOT NULL,
        category  TEXT DEFAULT 'Uncategorized',
        type      TEXT DEFAULT 'debit',
        UNIQUE(date, amount, merchant)
    );
    ''')
    conn.commit()
    conn.close()

def insert_expense(date: str, amount: float, merchant: str, category: str = "Uncategorized", exp_type: str = "debit"):
    """Inserts a single expense row into the database, ignoring duplicates."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
        INSERT OR IGNORE INTO expenses (date, amount, merchant, category, type)
        VALUES (?, ?, ?, ?, ?)
        ''', (date, amount, merchant, category, exp_type))
        conn.commit()
    finally:
        conn.close()

def get_recent_expenses(limit: int = 20, month: str = None) -> list[dict]:
    """
    Returns recent expenses, optionally filtered by month ("YYYY-MM").
    Ordered by date descending.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM expenses"
    params = []
    
    if month:
        query += " WHERE date LIKE ?"
        params.append(f"{month}-%")
        
    query += " ORDER BY date DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def get_category_summary(month: str) -> list[dict]:
    """
    Returns a summary of expenses aggregated by category for the given month ("YYYY-MM").
    Sorted by total descending.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT category, SUM(amount) as total
    FROM expenses
    WHERE date LIKE ? AND type = 'debit'
    GROUP BY category
    ORDER BY total DESC
    ''', (f"{month}-%",))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [{"category": row["category"], "total": row["total"]} for row in rows]

def execute_read_query(sql: str) -> list[dict]:
    """
    Executes a raw SELECT query against finance.db.
    Returns list of row dicts. Raises ValueError if query is not SELECT.
    
    Security note: We enforce read-only at the function level (not just the MCP layer)
    because this function may be called from multiple contexts. Defense-in-depth ensures
    even if the MCP validation is bypassed, the DB remains write-protected from arbitrary queries.
    """
    stripped = sql.strip()
    if not stripped.upper().startswith("SELECT"):
        raise ValueError("Only SELECT queries are permitted. Write operations are blocked.")
    
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(stripped)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        return [{"error": str(e)}]
    finally:
        conn.close()

def get_spending_anomalies(month: str) -> list[dict]:
    """
    Finds merchants where the given month's total spend is >50% higher
    than the average of the prior 3 months.

    Args:
        month: Target month in 'YYYY-MM' format (e.g. '2025-06').

    Returns:
        List of dicts with keys: merchant, current_month_total,
        three_month_avg, pct_increase.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
    WITH target AS (
        SELECT merchant, SUM(amount) AS current_total
        FROM expenses
        WHERE date LIKE ? AND type = 'debit'
        GROUP BY merchant
    ),
    prior AS (
        SELECT merchant, SUM(amount) / 3.0 AS avg_total
        FROM expenses
        WHERE date >= date(? || '-01', '-3 months')
          AND date <  ? || '-01'
          AND type = 'debit'
        GROUP BY merchant
    )
    SELECT
        t.merchant,
        t.current_total   AS current_month_total,
        COALESCE(p.avg_total, 0) AS three_month_avg,
        CASE
            WHEN COALESCE(p.avg_total, 0) = 0 THEN NULL
            ELSE ROUND((t.current_total - p.avg_total) / p.avg_total * 100, 1)
        END AS pct_increase
    FROM target t
    LEFT JOIN prior p ON t.merchant = p.merchant
    WHERE COALESCE(p.avg_total, 0) = 0
       OR t.current_total > p.avg_total * 1.5
    ORDER BY t.current_total DESC
    ''', (f"{month}-%", month, month))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]

# --- Session History (V2) ---

def init_sessions_table():
    """Creates the sessions table for persisting dashboard chart history."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sessions (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp  TEXT NOT NULL,
        query      TEXT,
        chart_type TEXT NOT NULL,
        title      TEXT NOT NULL,
        data_json  TEXT NOT NULL,
        summary    TEXT NOT NULL
    );
    ''')
    conn.commit()
    conn.close()

def insert_session(timestamp: str, query: str, chart_type: str, title: str, data_json: str, summary: str) -> int:
    """Inserts a session record and returns the new session id."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
        INSERT INTO sessions (timestamp, query, chart_type, title, data_json, summary)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (timestamp, query, chart_type, title, data_json, summary))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()

def get_all_sessions() -> list[dict]:
    """Returns all sessions ordered by timestamp descending."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM sessions ORDER BY timestamp DESC')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def delete_session(session_id: int) -> bool:
    """Deletes a session by id. Returns True if deleted, False if not found."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM sessions WHERE id = ?', (session_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()
