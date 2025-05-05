"""POS Streamlit App Scaffold"""

import streamlit as st
import os
import uuid
from datetime import datetime
from dotenv import load_dotenv
from pyzbar.pyzbar import decode
from PIL import Image
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Load environment variables
load_dotenv()

# Google Sheets setup
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
creds = ServiceAccountCredentials.from_json_keyfile_name(
    os.getenv("GOOGLE_OAUTH_CLIENT_SECRETS"), scope
)
gc = gspread.authorize(creds)

# Load sheet references
inventory_sheet = gc.open_by_url(os.getenv("SHEET_URL_INVENTORY")).sheet1
sales_sheet = gc.open_by_url(os.getenv("SHEET_URL_SALES")).sheet1
sessions_sheet = gc.open_by_url(os.getenv("SHEET_URL_SESSIONS")).sheet1


# Utility functions
def lookup_inventory(barcode):
    inventory_data = inventory_sheet.get_all_records()
    for item in inventory_data:
        if str(item.get("Barcode", "")) == str(barcode):
            return {
                "Item Name": item.get("Item Name"),
                "Price": float(item.get("Unit Price", 0)),
            }
    return None


def fallback_select_item(barcode):
    inventory_data = inventory_sheet.get_all_records()
    item_names = [item["Item Name"] for item in inventory_data if item["Item Name"]]
    selected = st.selectbox(
        "Item not found. Select item manually:", item_names, key=f"fallback_{barcode}"
    )
    if selected:
        matched = next((i for i in inventory_data if i["Item Name"] == selected), None)
        if matched:
            return {
                "Item Name": matched.get("Item Name"),
                "Price": float(matched.get("Unit Price", 0)),
            }
    return None


def add_to_cart(item):
    if "cart" not in st.session_state:
        st.session_state["cart"] = []
    for existing in st.session_state["cart"]:
        if existing["Item Name"] == item["Item Name"]:
            existing["Quantity"] += 1
            existing["Sub Total"] = existing["Quantity"] * existing["Price"]
            return
    st.session_state["cart"].append(
        {
            "Item Name": item["Item Name"],
            "Quantity": 1,
            "Price": item["Price"],
            "Sub Total": item["Price"],
        }
    )


def display_cart():
    if "cart" not in st.session_state or not st.session_state["cart"]:
        st.write("Cart is empty.")
        return
    df = pd.DataFrame(st.session_state["cart"])
    st.dataframe(df)


def checkout(pos_method, duty_person):
    if "cart" not in st.session_state or not st.session_state["cart"]:
        st.warning("Cart is empty. Cannot checkout.")
        return
    order_id = str(uuid.uuid4())[:8]
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    order_total = sum(item["Sub Total"] for item in st.session_state["cart"])

    for item in st.session_state["cart"]:
        sales_sheet.append_row(
            [
                order_id,
                now,
                item["Item Name"],
                item["Quantity"],
                item["Price"],
                item["Sub Total"],
                order_total,
                pos_method,
                duty_person,
            ]
        )
    st.success(f"Order {order_id} saved!")
    st.session_state["cart"] = []


def fetch_sales_by_date(date):
    rows = sales_sheet.get_all_records()
    df = pd.DataFrame(rows)
    if "Date & Time" in df.columns:
        df["Date Only"] = pd.to_datetime(df["Date & Time"]).dt.date
        return df[df["Date Only"] == date].drop(columns=["Date Only"])
    return pd.DataFrame()


# Main application


def main():
    st.set_page_config(
        page_title="Shop POS System",
        layout="wide",
        page_icon="🛒",
        initial_sidebar_state="expanded",
    )
    st.title("🛒 Shop POS System")

    if "credentials" not in st.session_state:
        st.session_state["credentials"] = {
            "id_token": {"email": "test_user@example.com"}
        }

    choice = st.sidebar.selectbox("Menu", ["New Sale", "Reports"], index=0)
    if choice == "New Sale":
        new_sale()
    else:
        reports()


def new_sale():
    st.header("New Sale")
    col1, col2 = st.columns(2)

    with col1:
        img_file = st.camera_input("Scan Barcode")
        if img_file:
            img = Image.open(img_file)
            decoded = decode(img)
            if decoded:
                code = decoded[0].data.decode("utf-8")
                item = lookup_inventory(code)
                if item:
                    add_to_cart(item)
                else:
                    fallback = fallback_select_item(code)
                    if fallback:
                        add_to_cart(fallback)

    with col2:
        display_cart()
        pos_method = st.selectbox("POS Method", ["Cash", "Jazzcash", "Easypaisa"])
        duty_person = st.session_state["credentials"]["id_token"].get(
            "email", "Unknown"
        )
        if st.button("Checkout"):
            checkout(pos_method, duty_person)


def reports():
    st.header("Sales Reports")
    selected_date = st.date_input("Select Date", datetime.utcnow().date())
    data = fetch_sales_by_date(selected_date)
    if not data.empty:
        st.write(data)
        csv = data.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download CSV", csv, f"sales_{selected_date}.csv", "text/csv"
        )
    else:
        st.info("No sales on this date.")


if __name__ == "__main__":
    main()
