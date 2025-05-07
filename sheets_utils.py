from googleapiclient.discovery import build
import datetime
import os
from dotenv import load_dotenv
import uuid
import ssl

load_dotenv()
# Setup Sheets API
SHEET_ID = os.getenv("SHEET_ID")  # Replace with your actual Google Sheet ID

# Disable SSL verification
ssl._create_default_https_context = ssl._create_unverified_context


def get_sheets_service(creds):
    """
    Build and return the Sheets API service using OAuth credentials.
    """
    return build("sheets", "v4", credentials=creds)


def get_inventory_items(creds):
    """
    Retrieve inventory items from the Google Sheet.
    """
    service = get_sheets_service(creds)
    sheet = service.spreadsheets()
    result = (
        sheet.values().get(spreadsheetId=SHEET_ID, range="Inventory!A2:A").execute()
    )
    values = result.get("values", [])
    return [row[0] for row in values if row]


def price_list(creds):
    service = get_sheets_service(creds)
    sheet = service.spreadsheets()
    # Fetch the Price data from the "Price List" sheet
    try:
        price_data = (
            sheet.values()
            .get(spreadsheetId=SHEET_ID, range="'Price List'!A2:C")
            .execute()
        )
        price_values = price_data.get("values", [])
        price_dict = {
            row[0]: float(row[2]) for row in price_values if len(row) >= 3
        }  # Map Item -> Price

        return price_dict
    except Exception:
        return


def write_sales_entries(items: list, duty_person, pos, creds):
    """
    Write sales entries to the Google Sheet, including all columns.
    Fetch the price dynamically from the Price List sheet.
    """
    data = []
    service = get_sheets_service(creds)
    sheet = service.spreadsheets()

    price_dict = price_list(creds)

    # Generate a single Order ID for the entire order
    order_id = str(uuid.uuid4())  # Generate a unique identifier for the order
    timestamp = datetime.datetime.now().isoformat()  # Current date & time

    # Calculate Order Total
    order_total = 0
    for item in items:
        item_name = item["item_name"]
        price = price_dict.get(item_name, 0)  # Default to 0 if the item is not found
        quantity = item["quantity"]
        sub_total = price * quantity  # Calculate Sub Total
        order_total += sub_total  # Add to Order Total

    # Create rows for each item
    for index, item in enumerate(items):
        item_name = item["item_name"]
        price = price_dict.get(item_name, 0)  # Default to 0 if the item is not found
        quantity = item["quantity"]
        sub_total = price * quantity  # Calculate Sub Total

        # Add Order Total only for the first row of the order
        row = [
            order_id,  # Single Order ID for the entire order (Column A)
            timestamp,  # Date & Time (Column B)
            item_name,  # Item Name (Column C)
            quantity,  # Quantity (Column D)
            price,  # Price (Column E)
            sub_total,  # Sub Total (Column F)
            (
                order_total if index == 0 else ""
            ),  # Order Total (Column G, only for the first row)
            pos,  # POS (Column H)
            duty_person,  # Duty Person (Column I)
        ]
        data.append(row)

    try:
        sheet.values().append(
            spreadsheetId=SHEET_ID,
            range="Sales!A2",  # Start appending from column A, row 2
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",  # Ensures proper row insertion
            body={"values": data},
        ).execute()
    except Exception as e:
        print(f"Error while entering {e}.")


def record_session(creds, email, session_token):
    """
    Record a user session in the Google Sheet.
    """
    service = get_sheets_service(creds)
    sheet = service.spreadsheets()
    timestamp = datetime.datetime.now().isoformat()
    data = [[timestamp, session_token, email]]
    sheet.values().append(
        spreadsheetId=SHEET_ID,
        range="Sessions!A2",
        valueInputOption="USER_ENTERED",
        body={"values": data},
    ).execute()