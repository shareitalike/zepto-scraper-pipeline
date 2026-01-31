
import asyncio
import logging
import random
import os
import csv
from datetime import datetime
import pandas as pd
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from scrapers.zepto import ZeptoScraper

# Configuration
# Configuration
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
INPUT_DIR = os.path.join(DATA_DIR, "input")
OUTPUT_DIR = os.path.join(DATA_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

INPUT_FILE = os.path.join(INPUT_DIR, "pin_codes_100.xlsx")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, f"zepto_availability_parallel_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
MAX_WORKERS = 4

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Zepto_Availability_Runner")

async def writer_task(queue: asyncio.Queue, filename: str):
    """Listens for data batches and appends to CSV."""
    file_initialized = False
    
    while True:
        try:
            batch = await queue.get()
            if batch is None:
                queue.task_done()
                break
                
            if batch:
                mode = 'a' if file_initialized else 'w'
                with open(filename, mode, newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=batch[0].keys())
                    if not file_initialized:
                        writer.writeheader()
                        file_initialized = True
                    writer.writerows(batch)
                logger.info(f"💾 Saved {len(batch)} availability records.")
            
            queue.task_done()
        except Exception as e:
            logger.error(f"Writer task error: {e}")

async def worker(name: str, item_queue: asyncio.Queue, result_queue: asyncio.Queue):
    """
    Worker:
    1. Gets (URL, Pincode)
    2. Scrapes Availability
    3. Pushes to Result Queue
    """
    logger.info(f"Worker {name} starting...")
    scraper = ZeptoScraper(headless=True)
    
    try:
        await scraper.start()
        
        while True:
            try:
                item = item_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            
            url, pincode = item
            logger.info(f"[{name}] Checking {url} at {pincode}")
            
            try:
                # Scrape Availability
                products = await scraper.scrape_availability(url, pincode)
                
                if products:
                    await result_queue.put(products)
                else:
                    logger.warning(f"[{name}] No data for {url}")
                
            except Exception as e:
                logger.error(f"[{name}] Failed {url}: {e}")
                
            item_queue.task_done()
            
            # Delay
            await scraper.human_delay(1, 3)
                
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
        # Expecting 'url' and 'pincode' columns (case insensitive cleanup)
        df.columns = [c.lower().strip() for c in df.columns]
        
        if 'url' not in df.columns: # or 'link'
             # Try finding link column
             link_col = next((c for c in df.columns if 'link' in c or 'url' in c), None)
             if link_col: df.rename(columns={link_col: 'url'}, inplace=True)
             
        if 'pincode' not in df.columns:
             p_col = next((c for c in df.columns if 'pin' in c), None)
             if p_col: df.rename(columns={p_col: 'pincode'}, inplace=True)

        if 'url' not in df.columns:
            logger.error("Input file must have 'url' or 'link' column")
            return

        items = []
        for _, row in df.iterrows():
            u = row.get('url')
            p = str(row.get('pincode', '560001')).split('.')[0] # Default logical pincode if missing?
            if pd.notna(u):
                items.append((u, p))
        
        logger.info(f"Loaded {len(items)} URL/Pincode pairs.")
        
    except Exception as e:
        logger.error(f"Failed to read input: {e}")
        return

    # 2. Setup Queues
    item_queue = asyncio.Queue()
    result_queue = asyncio.Queue()
    
    for i in items:
        item_queue.put_nowait(i)

    # 3. Launch Writer
    writer = asyncio.create_task(writer_task(result_queue, OUTPUT_FILE))

    # 4. Launch Workers
    workers = []
    actual_workers = min(MAX_WORKERS, len(items))
    
    for i in range(actual_workers):
        w = asyncio.create_task(worker(f"W-{i+1}", item_queue, result_queue))
        workers.append(w)
        await asyncio.sleep(random.uniform(1, 2))

    # Wait for workers
    await asyncio.gather(*workers)
    
    # Signal writer to stop
    await result_queue.put(None)
    await writer
    
    logger.info(f"All done! Output saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(main())
