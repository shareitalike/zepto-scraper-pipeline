
import asyncio
import csv
import argparse
import os
import logging
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from database import Database

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Zepto_Uploader")

def clean_csv_keys(row: dict) -> dict:
    """
    Cleans CSV row keys to match Supabase schema if necessary.
    Converts numeric strings to proper types.
    """
    cleaned = dict(row)
    
    # Rename columns to match Supabase schema (if needed)
    # Zepto CSV -> Supabase Column
    mapping = {
        "Item Name": "name",
        "Brand": "brand",
        "Mrp": "mrp",
        "Price": "price",
        "Weight/pack_size": "pack_size",
        "Category": "category",
        "Subcategory": "subcategory",
        "Delivery ETA": "eta",
        "timestamp": "scraped_at"
    }
    
    for old_key, new_key in mapping.items():
        if old_key in cleaned:
            cleaned[new_key] = cleaned.pop(old_key)
            
    # Remove unused keys or keys that don't match table
    # We keep: name, brand, mrp, price, pack_size, category, subcategory, availability, inventory, store_id, base_product_id, shelf_life_in_hours, scraped_at, pincode_input
    
    # Type conversion
    numeric_fields = ['price', 'mrp', 'inventory']
    for key in numeric_fields:
        if key in cleaned:
            val = cleaned[key]
            if val is None or val == "" or val == "N/A":
                cleaned[key] = None
                # Special handling for inventory "N/A" -> None
            else:
                try:
                    if key in ['price', 'mrp']:
                        cleaned[key] = float(val)
                    else:
                        cleaned[key] = int(float(val))
                except:
                    cleaned[key] = None

    # Filter only allowed columns (approximate list based on DB schema assumptions)
    # If the table is dynamic or has specific cols, extra keys might cause error
    # Let's clean up empty strings to None
    for k, v in cleaned.items():
        if v == "":
            cleaned[k] = None
            
    return cleaned

def main():
    parser = argparse.ArgumentParser(description="Upload Zepto CSV Data to Supabase")
    parser.add_argument("file", type=str, help="Path to the CSV file to upload")
    parser.add_argument("--table", type=str, default="zepto_assortment", help="Target Supabase table name")
    args = parser.parse_args()

    if not os.path.exists(args.file):
        logger.error(f"File {args.file} does not exist.")
        return

    db = Database()
    if not db.client:
        logger.error("Database connection failed. Check .env file.")
        return

    records = []
    logger.info(f"Reading {args.file}...")
    
    try:
        with open(args.file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append(clean_csv_keys(row))
                
        if not records:
            logger.warning("No records found in CSV.")
            return

        # Upload in batches of 100
        batch_size = 100
        total_batches = (len(records) + batch_size - 1) // batch_size
        
        logger.info(f"Found {len(records)} records. Uploading in {total_batches} batches...")
        
        for i in range(total_batches):
            batch = records[i*batch_size : (i+1)*batch_size]
            success = db.save_products(batch, table_name=args.table)
            if success:
                logger.info(f"Batch {i+1}/{total_batches} uploaded.")
            else:
                logger.error(f"Batch {i+1}/{total_batches} failed.")
                
        logger.info("Upload process completed.")
        
    except Exception as e:
        logger.error(f"Error processing file: {e}")

if __name__ == "__main__":
    main()
