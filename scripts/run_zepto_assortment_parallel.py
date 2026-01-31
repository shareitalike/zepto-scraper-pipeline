
import asyncio
import logging
import random
import os
import csv
import subprocess
from datetime import datetime
import pandas as pd
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from scrapers.zepto import ZeptoScraper

# Configuration
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
INPUT_DIR = os.path.join(DATA_DIR, "input")
OUTPUT_DIR = os.path.join(DATA_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

INPUT_FILE = os.path.join(INPUT_DIR, "pin_codes_40.xlsx")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, f"zepto_assortment_parallel_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
PERF_FILE = os.path.join(OUTPUT_DIR, f"zepto_performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
MAX_WORKERS = 4 

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Zepto_Assortment_Runner")

async def writer_task(queue: asyncio.Queue, filename: str):
    """Listens for data batches and appends to CSV."""
    file_initialized = False
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = None
        while True:
            try:
                batch = await queue.get()
                if batch is None: # Poison pill
                    queue.task_done()
                    break
                    
                # Filter valid products
                valid_products = [p for p in batch if isinstance(p, dict) and ('Price' in p or 'Item Name' in p)]
                
                if valid_products:
                    if not file_initialized:
                        writer = csv.DictWriter(f, fieldnames=valid_products[0].keys())
                        writer.writeheader()
                        file_initialized = True
                    
                    if writer:
                        writer.writerows(valid_products)
                        f.flush() # Ensure data is written
                        
                    logger.info(f"💾 Saved {len(valid_products)} products to CSV.")
                
                queue.task_done()
            except Exception as e:
                logger.error(f"Writer task error: {e}")

async def performance_writer_task(queue: asyncio.Queue, filename: str):
    """Listens for performance metrics and appends to CSV."""
    fields = ['Pincode', 'Status', 'Categories_Scraped', 'Products_Found', 'Start_Time', 'End_Time', 'Duration_Seconds', 'Error_Message']
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        
        while True:
            try:
                record = await queue.get()
                if record is None: # Poison pill
                    queue.task_done()
                    break
                
                writer.writerow(record)
                f.flush()
                
                logger.info(f"📊 Saved performance record for {record.get('Pincode')}")
                queue.task_done()
            except Exception as e:
                logger.error(f"Performance writer task error: {e}")

async def worker(name: str, pin_queue: asyncio.Queue, result_queue: asyncio.Queue, perf_queue: asyncio.Queue):
    """
    Worker:
    1. Gets Pincode
    2. Scrapes *All* Categories for that pincode
    3. Pushes data to Result Queue
    4. Pushes stats to Performance Queue
    """
    logger.info(f"Worker {name} starting...")
    scraper = ZeptoScraper(headless=True)
    
    try:
        await scraper.start()
        
        while True:
            try:
                pincode = pin_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            
            logger.info(f"[{name}] Starting Pincode: {pincode}")
            start_time = datetime.now()
            products_count = 0
            categories_count = 0
            status = "Success"
            error_msg = ""
            
            try:
                # 1. Set Location
                await scraper.set_location(pincode)
                
                # 2. Get Categories
                await asyncio.sleep(2)
                categories = await scraper.get_all_categories()
                categories_count = len(categories)
                logger.info(f"[{name}] Found {len(categories)} categories to scrape for {pincode}")
                
                # Scrape all categories
                for cat_url in categories:
                    try:
                        logger.info(f"[{name}] Fast Scraping {cat_url}...")
                        products = await scraper.scrape_assortment_fast(cat_url, pincode=pincode)
                        
                        if products:
                            products_count += len(products)
                            # Push to writer
                            await result_queue.put(products)
                        
                        # Short delay between categories for fast mode
                        await asyncio.sleep(0.1)
                        
                    except Exception as e:
                        logger.error(f"[{name}] Failed category {cat_url}: {e}")
                
            except Exception as e:
                logger.error(f"[{name}] Failed processing {pincode}: {e}")
                status = "Failed"
                error_msg = str(e)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Send Performance Record
            perf_record = {
                'Pincode': pincode,
                'Status': status,
                'Categories_Scraped': categories_count,
                'Products_Found': products_count,
                'Start_Time': start_time.isoformat(),
                'End_Time': end_time.isoformat(),
                'Duration_Seconds': duration,
                'Error_Message': error_msg
            }
            await perf_queue.put(perf_record)
                
            pin_queue.task_done()
            
            # Anti-ban break
            delay = random.uniform(5, 10)
            logger.info(f"[{name}] Finished {pincode}. Cooling down for {delay:.0f}s...")
            await asyncio.sleep(delay)
                
    except Exception as e:
        logger.error(f"[{name}] Crashed: {e}")
    finally:
        await scraper.stop()
        logger.info(f"Worker {name} retired.")

async def main():
    if not os.path.exists(INPUT_FILE):
        logger.error(f"Input file {INPUT_FILE} not found.")
        return

    # 1. Read Inputs
    try:
        df = pd.read_excel(INPUT_FILE)
        # Handle 'Pincode' or 'pincode' case insensitive
        col = next((c for c in df.columns if c.lower() == 'pincode'), None)
        if not col:
            logger.error("Input file must have 'Pincode' column")
            return
            
        raw_pincodes = df[col].dropna().astype(str).tolist()
        pincodes = []
        for p in raw_pincodes:
            # Handle multiple pincodes in one cell (comma separated)
            parts = [x.strip() for x in p.split(',')]
            for part in parts:
                clean_p = part.split('.')[0].strip()
                if clean_p.isdigit() and len(clean_p) == 6:
                    pincodes.append(clean_p)
        
        pincodes = sorted(list(set(pincodes)))
        logger.info(f"Loaded {len(pincodes)} unique pincodes.")
    except Exception as e:
        logger.error(f"Failed to read input: {e}")
        return

    # 2. Setup Queues
    pin_queue = asyncio.Queue()
    result_queue = asyncio.Queue()
    perf_queue = asyncio.Queue()
    
    for p in pincodes:
        pin_queue.put_nowait(p)

    # 3. Launch Writers
    writer = asyncio.create_task(writer_task(result_queue, OUTPUT_FILE))
    perf_writer = asyncio.create_task(performance_writer_task(perf_queue, PERF_FILE))

    # 4. Launch Workers
    workers = []
    actual_workers = min(MAX_WORKERS, len(pincodes))
    
    for i in range(actual_workers):
        w = asyncio.create_task(worker(f"W-{i+1}", pin_queue, result_queue, perf_queue))
        workers.append(w)
        await asyncio.sleep(random.uniform(2, 5))

    # Wait for workers
    await asyncio.gather(*workers)
    
    # Signal writers to stop
    await result_queue.put(None)
    await perf_queue.put(None)
    
    await writer
    await perf_writer
    
    logger.info(f"All done! \nData: {OUTPUT_FILE}\nPerformance: {PERF_FILE}")

    # Trigger Upload
    logger.info("🚀 Starting automatic upload to Supabase...")
    try:
        uploader_script = os.path.join(os.path.dirname(__file__), "upload_zepto_data.py")
        subprocess.run(["python", uploader_script, OUTPUT_FILE], check=True)
        logger.info("✅ Upload complete. Dashboard is updated!")
        print("\n\n" + "="*50)
        print(" EXECUTION COMPLETE ")
        print("="*50)
        print(f"1. Scraped Data:   {OUTPUT_FILE}")
        print(f"2. Performance:    {PERF_FILE}")
        print("3. Dashboard:      Visit http://localhost:8501 and click 'Refresh Data'")
        print("="*50 + "\n")
    except Exception as e:
         logger.error(f"Failed to auto-upload: {e}")

if __name__ == "__main__":
    asyncio.run(main())
