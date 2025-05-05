import os
from datetime import datetime
from dotenv import load_dotenv
from oauth_sheets import get_sheets_service

# Load environment variables from .env
load_dotenv()

# Single Google Sheets file ID (env var must be set)
SHEET_ID = os.getenv("SPREADSHEET_ID")
if not SHEET_ID:
    raise ValueError("Missing SPREADSHEET_ID in environment")


def lookup_product(barcode: str, session_key: str):
    """
    Look up an item name by barcode in the Inventory tab.
    Returns a dict: { 'item_name': str } or None if not found.
    """
    svc = get_sheets_service(session_key)
    # Read Inventory tab (assumes header row at A1)
    result = (
        svc.spreadsheets()
        .values()
        .get(spreadsheetId=SHEET_ID, range="Inventory!A1:Z1000")
        .execute()
    )
    values = result.get("values", [])
    if len(values) < 2:
        return None
    headers = values[0]
    for row in values[1:]:
        data = dict(zip(headers, row))
        if data.get("Barcode") == barcode:
            return {"item_name": data.get("Item Name")}
    return None


def get_next_order_id(session_key: str) -> int:
    """
    Determine the next Order ID by reading the Sales tab.
    """
    svc = get_sheets_service(session_key)
    result = (
        svc.spreadsheets()
        .values()
        .get(spreadsheetId=SHEET_ID, range="Sales!A2:A10000")
        .execute()
    )
    values = result.get("values", [])
    ids = [int(r[0]) for r in values if r and r[0].isdigit()]
    return max(ids, default=0) + 1


def append_order(
    session_key: str, order_id: int, date_time: str, pos: str, duty: str, lines: list
):
    """
    Append one row per line-item to the Sales tab.
    Columns written: Order ID, Date & Time, Item Name, Quantity, [blanks], POS, Duty Person.
    """
    svc = get_sheets_service(session_key)
    # Build rows, leaving price/subtotal/total for sheet formulas
    values = [
        [
            order_id,
            date_time,
            l["item_name"],
            l["quantity"],
            "",  # Price (auto)
            "",  # Subtotal (auto)
            "",  # Order Total (auto)
            pos,
            duty,
        ]
        for l in lines
    ]
    svc.spreadsheets().values().append(
        spreadsheetId=SHEET_ID,
        range="Sales!A1",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": values},
    ).execute()


def log_session(session_key: str, email: str):
    """
    Log each login session into the Sessions tab.
    """
    svc = get_sheets_service(session_key)
    ts = datetime.utcnow().isoformat()
    svc.spreadsheets().values().append(
        spreadsheetId=SHEET_ID,
        range="Sessions!A1",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": [[ts, session_key, email]]},
    ).execute()


def summarize_date(date_str: str, session_key: str) -> float:
    """
    Sum all Order Total values for orders on a given date.
    """
    svc = get_sheets_service(session_key)
    result = (
        svc.spreadsheets()
        .values()
        .get(spreadsheetId=SHEET_ID, range="Sales!A2:I10000")
        .execute()
    )
    rows = result.get("values", [])
    total = 0.0
    for row in rows:
        if row[1].startswith(date_str):
            try:
                total += float(row[6])
            except:
                continue
    return total
