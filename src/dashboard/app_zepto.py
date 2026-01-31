
import streamlit as st
import pandas as pd
import plotly.express as px
import sys
import os
import subprocess

# Add parent directory to path to import database
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import Database

st.set_page_config(page_title="Zepto Analytics Dashboard", layout="wide")

st.title("⚡ Zepto Assortment & Availability Dashboard")

# Initialize DB
@st.cache_resource
def get_db():
    return Database()

db = get_db()
if not db.client:
    st.error("❌ Database connection failed. Please check your `.env` file credentials.")
    st.stop()

# Fetch Data
@st.cache_data(ttl=600)
def load_data():
    data = db.fetch_products(table_name="zepto_assortment", limit=5000)
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    
    # Ensure numeric columns
    for col in ['price', 'mrp', 'inventory']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
    # Process Dates
    if 'scraped_at' in df.columns:
        df['scraped_at'] = pd.to_datetime(df['scraped_at'])
        df['scrape_time_str'] = df['scraped_at'].dt.strftime('%d-%m-%Y %H:%M:%S')
        df['date'] = df['scraped_at'].dt.date

    if 'created_at' in df.columns:
        df['created_at'] = pd.to_datetime(df['created_at'])
        try:
            # Convert UTC to IST
            if df['created_at'].dt.tz is None:
                df['created_at'] = df['created_at'].dt.tz_localize('UTC')
            df['created_at'] = df['created_at'].dt.tz_convert('Asia/Kolkata')
        except: pass
        df['created_time_str'] = df['created_at'].dt.strftime('%d-%m-%Y %H:%M:%S')
            
    return df

with st.spinner("Loading data from Supabase..."):
    df = load_data()

if df.empty:
    st.warning("No data found in database `zepto_assortment`. Run scraper and upload data first.")
    # We don't stop here anymore so controls can be used even if empty

# Sidebar Filters
st.sidebar.header("Filters")

# Time Filters
if 'scrape_time_str' in df.columns:
    available_times = sorted(df['scrape_time_str'].unique(), reverse=True)
    scrape_time_filter = st.sidebar.multiselect("Select Scrape Time", options=available_times, default=available_times[:1] if available_times else [])
else:
    scrape_time_filter = []

if 'created_time_str' in df.columns:
    available_created = sorted(df['created_time_str'].unique(), reverse=True)
    created_time_filter = st.sidebar.multiselect("Select DB Upload Time", options=available_created)
else:
    created_time_filter = []

if 'pincode_input' in df.columns:
    pincode_filter = st.sidebar.multiselect("Select Pincode", options=df['pincode_input'].unique())
else:
    pincode_filter = []

if 'category' in df.columns:
    category_filter = st.sidebar.multiselect("Select Category", options=df['category'].dropna().unique())
else:
    category_filter = []

st.sidebar.markdown("---")
if st.sidebar.button("🔄 Refresh Data"):
    st.cache_data.clear()

st.sidebar.markdown("---")
st.sidebar.markdown("---")
st.sidebar.header("🚀 Scraper Controls")

# Mode Selection
scrape_mode = st.sidebar.radio("Select Scrape Mode", ["Single Pincode (Assortment)", "Bulk Assortment (File)", "Bulk Availability (File)"])

if scrape_mode == "Single Pincode (Assortment)":
    pincode_input = st.sidebar.text_input("Enter Pincode", "560001")
    if st.sidebar.button("Run Scraper"):
        if not pincode_input:
            st.sidebar.error("Please enter a pincode!")
        else:
            try:
                subprocess.Popen(
                    [sys.executable, "scripts/run_zepto.py", "--pincode", pincode_input],
                    cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')),
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
                st.sidebar.success(f"Scraper started for {pincode_input}!")
            except Exception as e:
                st.sidebar.error(f"Failed to start scraper: {e}")

elif scrape_mode == "Bulk Assortment (File)":
    uploaded_file = st.sidebar.file_uploader("Upload pin_codes.xlsx", type=['xlsx'], key="assortment_uploader")
    if uploaded_file:
        try:
            # Save to data/input/pin_codes.xlsx
            save_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'input', "pin_codes.xlsx")
            with open(save_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.sidebar.success("✅ File saved!")
        except Exception as e:
            st.sidebar.error(f"Save failed: {e}")

    if st.sidebar.button("Run Bulk Assortment"):
        try:
            subprocess.Popen(
                [sys.executable, "scripts/run_zepto_assortment_parallel.py"],
                cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')),
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
            st.sidebar.success("Bulk Assortment Scraper started!")
        except Exception as e:
            st.sidebar.error(f"Failed to start: {e}")

elif scrape_mode == "Bulk Availability (File)":
    uploaded_file = st.sidebar.file_uploader("Upload pin_codes_100.xlsx", type=['xlsx'], key="avail_uploader")
    if uploaded_file:
        try:
            # Save to data/input
            save_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'input', "pin_codes_100.xlsx")
            with open(save_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.sidebar.success("✅ File saved!")
        except Exception as e:
            st.sidebar.error(f"Save failed: {e}")

    if st.sidebar.button("Run Bulk Availability"):
        try:
            subprocess.Popen(
                [sys.executable, "scripts/run_zepto_availability_parallel.py"],
                cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')),
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
            st.sidebar.success("Bulk Availability Scraper started!")
        except Exception as e:
            st.sidebar.error(f"Failed to start: {e}")

if df.empty:
    st.stop()

filtered_df = df.copy()

# Apply Filters
if scrape_time_filter:
    filtered_df = filtered_df[filtered_df['scrape_time_str'].isin(scrape_time_filter)]
if created_time_filter:
    filtered_df = filtered_df[filtered_df['created_time_str'].isin(created_time_filter)]
if pincode_filter:
    filtered_df = filtered_df[filtered_df['pincode_input'].isin(pincode_filter)]
if category_filter:
    filtered_df = filtered_df[filtered_df['category'].isin(category_filter)]

# Metrics
col1, col2, col3 = st.columns(3)
col1.metric("Total Products", len(filtered_df))

out_of_stock = len(filtered_df[filtered_df['availability'] == 'Out of Stock']) if 'availability' in filtered_df.columns else 0
col2.metric("Out of Stock", out_of_stock, delta_color="inverse")

cat_count = filtered_df['category'].nunique() if 'category' in filtered_df.columns else 0
col3.metric("Categories", cat_count)



# Data Grid
st.subheader("📋 Raw Data Explorer")
search_term = st.text_input("Search Product Name", "")
if search_term and 'name' in filtered_df.columns:
    filtered_df = filtered_df[filtered_df['name'].str.contains(search_term, case=False, na=False)]

# Select and Rename Columns for Client View
client_view = filtered_df.copy()

# Rename map based on Client Request
# DB Column -> Client Column
column_map = {
    'category': 'Category',
    'subcategory': 'Subcategory',
    'name': 'Item Name',
    'brand': 'Brand',
    'mrp': 'Mrp',
    'price': 'Price',
    'pack_size': 'Weight/pack_size',
    'eta': 'Delivery ETA',
    'availability': 'availability',
    'inventory': 'inventory',
    'store_id': 'store_id',
    'base_product_id': 'base_product_id',
    'shelf_life_in_hours': 'shelf_life_in_hours',
    'scraped_at': 'timestamp', 
    'pincode_input': 'pincode_input',
    'clicked_label': 'clicked_label'
}

# 1. Rename existing columns
client_view = client_view.rename(columns=column_map)

# 2. Keep only requested columns that exist
requested_cols = list(column_map.values())
final_cols = [c for c in requested_cols if c in client_view.columns]
client_view = client_view[final_cols]

st.dataframe(client_view, width="stretch")
