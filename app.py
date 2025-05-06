import streamlit as st
import uuid
import datetime
from auth_utils import (
    google_login,
    handle_oauth_callback,
    get_user_email,
    create_session,
)
from sheets_utils import get_inventory_items, write_sales_entries, record_session

# --- Handle OAuth ---
if "email" not in st.session_state:
    creds = handle_oauth_callback()
    if creds:
        email = get_user_email(creds)
        st.session_state["email"] = email
        st.session_state["session_token"] = create_session(email)
        st.session_state["creds"] = creds  # Store creds in session state
        # Pass creds to record_session
        record_session(creds, email, st.session_state["session_token"])

# --- Login Screen ---
if "email" not in st.session_state:
    st.title("POS System Login")
    google_login()
    st.stop()

# Retrieve creds from session state
creds = st.session_state.get("creds")  # Get creds from session state

# --- Sidebar ---
st.sidebar.write(f"Logged in as: {st.session_state['email']}")
if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.experimental_get_query_params()
    st.experimental_rerun()

# --- Main POS App ---
st.title("📦 Khaapa System")

# --- Load Inventory ---
if creds:  # Ensure creds is available
    inventory = get_inventory_items(creds)  # Pass creds to get_inventory_items
else:
    st.error("Authentication credentials are missing. Please log in again.")
    st.stop()

if "order_items" not in st.session_state:
    st.session_state["order_items"] = []

# --- Add Items to Order ---
st.subheader("🛒 Add Item to Order")
item = st.selectbox("Select Item", inventory)
qty = st.number_input("Quantity", min_value=1, value=1, step=1)
if st.button("Add to Order"):
    st.session_state["order_items"].append({"item_name": item, "quantity": qty})
    st.success(f"Added {qty} x {item}")

# --- Show Current Order ---
st.subheader("📝 Current Order")
if st.session_state["order_items"]:
    for i, entry in enumerate(st.session_state["order_items"]):
        st.write(f"{i + 1}. {entry['item_name']} × {entry['quantity']}")
else:
    st.info("No items added yet.")

# --- Checkout ---
st.subheader("✅ Checkout Order")
pos = st.selectbox(
    "Select POS", ["Cash", "Jaweria Easypaisa", "Ibrahim Jazzcash"]
)  # POS dropdown
if st.button("Submit Order"):
    if st.session_state["order_items"]:
        order_id = "ORD" + datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        print(st.session_state["order_items"])
        write_sales_entries(
            items=st.session_state["order_items"],
            duty_person=st.session_state["email"],
            pos=pos,  # Pass the selected POS value
            creds=creds,  # Pass creds to write_sales_entries
        )
        st.success(f"Order {order_id} submitted successfully!")
        st.session_state["order_items"] = []  # Reset order
    else:
        st.warning("No items to checkout.")
