import asyncio
import logging
import argparse
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from scrapers.zepto import ZeptoScraper

logging.basicConfig(level=logging.INFO)

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pincode", type=str, default="560001", help="Pincode to set")
    args = parser.parse_args()

    # Output directory
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'output')
    os.makedirs(output_dir, exist_ok=True)


    scraper = ZeptoScraper(headless=True)
    try:
        await scraper.start()
        await scraper.set_location(args.pincode)
        
        # Get all categories
        categories = await scraper.get_all_categories()
        logging.info(f"Found {len(categories)} categories to scrape")
        
        all_products = []
        import pandas as pd
        
        # Limit for testing?
        # categories = categories[:2] 
        
        for i, cat_url in enumerate(categories):
            logging.info(f"Processing {i+1}/{len(categories)}: {cat_url}")
            products = await scraper.scrape_assortment(cat_url, args.pincode)
            all_products.extend(products)
            
            # Save intermediate
            if len(all_products) > 0 and (i + 1) % 1 == 0:
                 pd.DataFrame(all_products).to_csv("zepto_products_partial_new_v4.csv", index=False)
                 logging.info(f"Saved partial CSV with {len(all_products)} products")
        
        # Final Save
        if all_products:
            df = pd.DataFrame(all_products)
            filename = os.path.join(output_dir, f"zepto_products_{args.pincode}.csv")
            df.to_csv(filename, index=False)
            logging.info(f"Saved {len(all_products)} products to {filename}")
        else:
            logging.warning("No products scraped")
            
        print("Done. Waiting 5s then exiting.")
        await asyncio.sleep(5)
    except Exception as e:
        logging.error(f"Error: {e}")
    finally:
        await scraper.stop()

if __name__ == "__main__":
    asyncio.run(main())
