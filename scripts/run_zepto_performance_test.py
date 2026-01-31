
import asyncio
import logging
import random
import os
import json
import time
import pandas as pd
from datetime import datetime
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

INPUT_FILE = os.path.join(INPUT_DIR, "pin_codes.xlsx")
METRICS_FILE = os.path.join(OUTPUT_DIR, "performance_metrics.json")
MAX_WORKERS = 4 
TEST_LIMIT = 5 # Limit to 5 pincodes for dry run

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Zepto_Perf_Test")

async def worker(name: str, pin_queue: asyncio.Queue, results: list):
    """
    Worker that tracks performance metrics.
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
            start_time = time.time()
            item_count = 0
            category_count = 0
            status = "Success"
            error_msg = ""
            
            try:
                # 1. Set Location
                await scraper.set_location(pincode)
                
                # 2. Get Categories
                categories = await scraper.get_all_categories()
                category_count = len(categories)
                
                # 3. Scrape Categories (Limit to 3 categories for speed in dry run, or all?)
                # User said "dry run for the pin codes for performance metrics"
                # If we limit categories, metrics are skewed. Let's do ALL but maybe for fewer pincodes.
                # We already stuck to TEST_LIMIT pincodes.
                
                for cat_url in categories:
                    try:
                        # USE FAST MODE
                        products = await scraper.scrape_assortment_fast(cat_url, pincode=pincode)
                        item_count += len(products)
                        # Minimal delay for API internal throttling if needed, but fetch is resilient
                        await asyncio.sleep(0.1) 
                    except Exception as e:
                        logger.error(f"[{name}] Failed category {cat_url}: {e}")
                
            except Exception as e:
                logger.error(f"[{name}] Failed processing {pincode}: {e}")
                status = "Failed"
                error_msg = str(e)
                
            duration = time.time() - start_time
            
            # Record Metric for this pincode
            metric = {
                "pincode": pincode,
                "worker": name,
                "duration_seconds": round(duration, 2),
                "items_scraped": item_count,
                "categories_found": category_count,
                "status": status,
                "error": error_msg,
                "timestamp": datetime.now().isoformat()
            }
            results.append(metric)
            
            pin_queue.task_done()
            
            delay = random.uniform(2, 5)
            await asyncio.sleep(delay)
                
    except Exception as e:
        logger.error(f"[{name}] Crashed: {e}")
    finally:
        await scraper.stop()

async def main():
    if not os.path.exists(INPUT_FILE):
        logger.error(f"Input file {INPUT_FILE} not found.")
        return

    # 1. Read Inputs
    try:
        df = pd.read_excel(INPUT_FILE)
        col = next((c for c in df.columns if c.lower() == 'pincode'), None)
        if not col:
            logger.error("Input file must have 'Pincode' column")
            return
            
        raw_pincodes = df[col].dropna().astype(str).tolist()
        pincodes = []
        for p in raw_pincodes:
             parts = [x.strip() for x in p.split(',')]
             for part in parts:
                clean_p = part.split('.')[0].strip()
                if clean_p.isdigit() and len(clean_p) == 6:
                    pincodes.append(clean_p)
        
        pincodes = sorted(list(set(pincodes)))
        
        # Limit for Dry Run
        pincodes = pincodes[:TEST_LIMIT]
        logger.info(f"Loaded {len(pincodes)} pincodes for DRY RUN.")
        
    except Exception as e:
        logger.error(f"Failed to read input: {e}")
        return

    # 2. Setup Queue & Results
    pin_queue = asyncio.Queue()
    results = [] # Shared list (not thread safe but okay for coroutines if just appending?)
    # Asyncio is single threaded so append is safe.
    
    for p in pincodes:
        pin_queue.put_nowait(p)

    # 3. Launch Workers
    start_total = time.time()
    workers = []
    actual_workers = min(MAX_WORKERS, len(pincodes))
    
    for i in range(actual_workers):
        w = asyncio.create_task(worker(f"W-{i+1}", pin_queue, results))
        workers.append(w)
        await asyncio.sleep(1)

    # Wait for workers
    await asyncio.gather(*workers)
    
    total_duration = time.time() - start_total
    
    # 4. Calculate Aggregate Metrics
    total_items = sum(r['items_scraped'] for r in results)
    successful_pins = sum(1 for r in results if r['status'] == 'Success')
    avg_time = total_duration / len(pincodes) if pincodes else 0
    throughput = (total_items / (total_duration / 60)) if total_duration > 0 else 0
    
    final_report = {
        "test_timestamp": datetime.now().isoformat(),
        "total_duration_sec": round(total_duration, 2),
        "total_pincodes_attempted": len(pincodes),
        "successful_pincodes": successful_pins,
        "total_items_scraped": total_items,
        "average_time_per_pincode_sec": round(avg_time, 2),
        "throughput_items_per_min": round(throughput, 2),
        "details": results
    }
    
    # Save to JSON
    with open(METRICS_FILE, "w", encoding="utf-8") as f:
        json.dump(final_report, f, indent=2)
        
    logger.info(f"Performance Test Complete. Metrics saved to {METRICS_FILE}")
    print(json.dumps(final_report, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
