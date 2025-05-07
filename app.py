import streamlit as st
import datetime
from auth_utils import (
    google_login,
    handle_oauth_callback,
    get_user_email,
    create_session,
)
from sheets_utils import (
    get_inventory_items,
    write_sales_entries,
    record_session,
    price_list,
)

# Initialize session state for order_items and order_total
if "order_items" not in st.session_state:
    st.session_state["order_items"] = []  # Initialize as an empty list
if "order_total" not in st.session_state:
    st.session_state["order_total"] = 0  # Initialize as 0

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
    st.title("Khaapa Login")

    google_login()
    st.stop()

# Retrieve creds from session state
creds = st.session_state.get("creds")  # Get creds from session state

# --- Sidebar ---
st.sidebar.write(f"Logged in as: {st.session_state['email']}")
if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.query_params.clear()
    st.experimental_rerun()

# --- Main POS App ---
st.title("📦 Khaapa System")

# --- Load Inventory ---
if creds:  # Ensure creds is available
    inventory = get_inventory_items(creds)  # Pass creds to get_inventory_items
    if not inventory:
        st.error("No items found in the Inventory sheet. Please check the data.")
        st.stop()
else:
    st.error("Authentication credentials are missing. Please log in again.")
    st.stop()

# --- Add Items to Order ---
st.subheader("🛒 Add Item to Order")

# Select Item Manually
st.write("### Select Item")
item_name = st.selectbox("Select Item", list(inventory))
qty = st.number_input("Quantity", min_value=1, value=1, step=1)

if st.button("Add to Order"):
    # Add the selected item to the order
    st.session_state["order_items"].append({"item_name": item_name, "quantity": qty})
    st.success(f"Added {qty} x {item_name}")

# --- Show Current Order ---
st.subheader("📝 Current Order")
if st.session_state["order_items"]:
    # Create a table for the current order
    import pandas as pd

    # Add a price lookup logic (replace with actual logic if available)
    price_dict = price_list(creds)

    # Prepare data for the table
    order_data = []
    for entry in st.session_state["order_items"]:
        item_name = entry["item_name"]
        quantity = entry["quantity"]
        price = price_dict[item_name] * quantity
        order_data.append(
            {"Item Name": item_name, "Quantity": quantity, "Price": price}
        )

    # Convert to a DataFrame
    order_df = pd.DataFrame(order_data)

    # Display the table
    st.table(order_df)

    # Display the total price
    total_price = order_df["Price"].sum()
    st.write(f"**Total Price: {total_price}**")
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
        write_sales_entries(
            items=st.session_state["order_items"],
            duty_person=st.session_state["email"],
            pos=pos,  # Pass the selected POS value
            creds=creds,  # Pass creds to write_sales_entries
        )
        st.success(f"Order {order_id} submitted successfully!")
        st.session_state["order_items"] = []  # Reset order
        st.session_state["order_total"] = 0  # Reset order total
    else:
        st.warning("No items to checkout.")
