
import asyncio
from datetime import datetime
import logging
import json
import re
import time
from typing import List, Optional
from .base import BaseScraper
from .models import ProductItem
from urllib.parse import quote

logger = logging.getLogger(__name__)

class ZeptoScraper(BaseScraper):
    def __init__(self, headless=False):
        super().__init__(headless)
        self.base_url = "https://www.zepto.com/"
        self.delivery_eta = "N/A"
        self.store_id = "N/A"
        self.clicked_location_label = "N/A"

    async def set_location(self, pincode: str):
        logger.info(f"Setting location to {pincode}")
        try:
            await self.page.goto(self.base_url, timeout=60000, wait_until='domcontentloaded')
            await self.human_delay()

            # Location interaction logic
            try:
                trigger_selector = "button[aria-label='Select Location']"
                try:
                    await self.page.wait_for_selector(trigger_selector, timeout=10000)
                    await self.page.hover(trigger_selector)
                    await self.human_delay(0.5)
                    await self.page.click(trigger_selector, force=True)
                    logger.info("Clicked location trigger (force=True)")
                except:
                     logger.warning("Standard click failed, trying JS click...")
                     await self.page.evaluate(f"document.querySelector(\"{trigger_selector}\").click()")

                await self.page.wait_for_selector("input[type='text']", timeout=10000)
                logger.info("Modal/Input appeared")
                
            except Exception as e:
                logger.warning(f"Could not open location modal: {e}")
                # return # Continue anyway to see if we can scrape

            await self.human_delay()
            
            # Type Pincode
            input_selectors = [
                 "input[placeholder*='Search a new address']", 
                 "input[placeholder*='Search']",
                 "input[type='text']"
            ]
            
            found_input = False
            for sel in input_selectors:
                if await self.page.is_visible(sel):
                     input_selector = sel
                     found_input = True
                     break
            
            if found_input:
                try:
                    await self.page.click(input_selector)
                    await self.page.keyboard.press("Control+A")
                    await self.page.keyboard.press("Backspace")
                    await self.page.keyboard.type(pincode, delay=100)
                    logger.info(f"Typed pincode: {pincode}")
                    
                    await self.human_delay()
                    await self.human_delay()
                    # await self.page.keyboard.press("Enter")
                    # logger.info("Pressed Enter for location selection")
                    # await self.human_delay()

                    # Wait for results to appear
                    try:
                        await self.page.wait_for_selector("div[data-testid='location-search-item'], [data-testid='prediction-item'], div[class*='prediction'], div[class*='search-result']", timeout=5000)
                    except: pass
                    
                    # Click first result
                    if await self.page.is_visible("input[type='text']"):
                        # specific selectors for location results
                        results = await self.page.query_selector_all("div[data-testid='address-search-item'], [data-testid='location-search-item'], [data-testid='prediction-item']")
                        if not results:
                             results = await self.page.query_selector_all("div[class*='prediction'], div[class*='search-result']")
                             
                        if results:
                            # Capture the text of the prediction before clicking
                            try:
                                text = await results[0].inner_text()
                                # Clean up text (remove "Location" etc if needed)
                                if text:
                                    self.clicked_location_label = text.split('\n')[0].strip() # Take primary part
                                    logger.info(f"Captured clicked label: {self.clicked_location_label}")
                            except:
                                logger.warning("Could not capture clicked label text")

                            await results[0].click(force=True)
                            logger.info("Clicked first prediction result (force=True)")
                        else:
                             # Fallback if no preds
                             # content = await self.page.content()
                             # with open("debug_location_results.html", "w", encoding="utf-8") as f:
                             #    f.write(content)
                             # logger.info("Dumped HTML to debug_location_results.html")
                             
                             await self.page.keyboard.press("Enter")
                             logger.info("Fallback: Pressed Enter")
                except Exception as e:
                     logger.error(f"Could not type pincode: {e}")

            await self.human_delay()
            

            await self.human_delay()
            
            # Extract ETA
            try:
                # Try multiple selectors
                eta_el = await self.page.query_selector("div[data-testid='eta-container']")
                if not eta_el:
                     eta_el = await self.page.query_selector("p[class*='eta']")
                     
                if eta_el:
                    self.delivery_eta = await eta_el.inner_text()
                    logger.info(f"Captured ETA: {self.delivery_eta}")
                else:
                    # Fallback text search
                    content = await self.page.content()
                    eta_match = re.search(r'(\d+\s*mins?)', content, re.IGNORECASE)
                    if eta_match:
                         self.delivery_eta = eta_match.group(1)
                         logger.info(f"Captured ETA via regex: {self.delivery_eta}")

            except:
                logger.warning("Could not capture ETA")

            # Extract Store ID from page content
            try:
                content = await self.page.content()
                # storeId":"b4dc8d65-..."
                store_match = re.search(r'\"storeId\":\"([^\"]+)\"', content)
                if store_match:
                    self.store_id = store_match.group(1)
                    logger.info(f"Captured Store ID: {self.store_id}")
                else:
                    # Fallback
                    store_match_2 = re.search(r'store_?id\W+([a-zA-Z0-9\-]+)', content, re.IGNORECASE)
                    if store_match_2:
                         self.store_id = store_match_2.group(1)
                         logger.info(f"Captured Store ID via regex 2: {self.store_id}")
            except Exception as e:
                 logger.warning(f"Could not capture Store ID: {e}")

        except Exception as e:
            logger.error(f"Error setting location: {e}")

    async def get_all_categories(self) -> List[str]:
        logger.info("Extracting category links...")
        try:
            await self.page.wait_for_selector("a[href*='/cn/']", timeout=10000)
            hrefs = await self.page.evaluate("""
                () => {
                    return Array.from(document.querySelectorAll('a'))
                        .map(a => a.href)
                        .filter(href => href.includes('/cn/') && href.includes('/cid/'))
                }
            """)
            categories = list(set(hrefs))
            logger.info(f"Found {len(categories)} unique category links")
            return categories
        except Exception as e:
            logger.error(f"Error extracting categories: {e}")
            return []

    async def scrape_assortment(self, category_url: str, pincode: str = "N/A") -> List[ProductItem]:
        logger.info(f"Scraping {category_url}")
        products: List[ProductItem] = []
        captured_data = []

        async def handle_response(response):
            try:
                ct = response.headers.get("content-type", "").lower()
                if "image" in ct or "font" in ct or "css" in ct or "javascript" in ct:
                    return
                # Capture useful types
                if response.status == 200:
                    try:
                        data = await response.json()
                        captured_data.append({"url": response.url, "type": "json", "data": data})
                    except:
                         try:
                             text = await response.text()
                             # Save string data if length seems substantial (Flight data is large)
                             if len(text) > 10000 or "x-component" in ct:
                                 captured_data.append({"url": response.url, "type": ct, "data": text})
                         except: pass
            except: pass

        self.page.on("response", handle_response)

        try:
            await self.page.goto(category_url, timeout=60000)
            await self.human_delay(3)
            await self.human_scroll()
            await self.human_delay(2)
            
        except Exception as e:
            logger.error(f"Error navigating/scrolling: {e}")
        finally:
             self.page.remove_listener("response", handle_response)

        # Parse captured data
        logger.info(f"Captured {len(captured_data)} responses. Parsing...")
        
        # Extract Category/Sub from URL if possible
        cat_name = "Unknown"
        sub_name = "Unknown"
        try:
            if "/cn/" in category_url:
                parts = category_url.split("/cn/")[1].split("/")
                if len(parts) >= 2:
                    cat_name = parts[0].replace("-", " ").title()
                    sub_name = parts[1].replace("-", " ").title()
        except: pass

        # Helper to parse product from dict
        def parse_product_from_dict(p_data: dict) -> Optional[ProductItem]:
            try:
                # Common fields in Zepto JSON
                p_id = p_data.get("id")
                if not p_id: return None
                
                name = p_data.get("name") or p_data.get("productName")
                if not name: return None
                
                # Pricing
                mrp = str(p_data.get("mrp", 0) / 100) if p_data.get("mrp") else "N/A"
                price = str(p_data.get("sellingPrice", 0) / 100) if p_data.get("sellingPrice") else mrp
                if price == "0.0": price = mrp # Fallback
                
                # Inventory
                qty = p_data.get("availableQuantity", 0)
                inventory = str(qty)
                availability = "In Stock" if qty > 0 else "Out of Stock"
                
                # Meta
                pack_size = p_data.get("packsize") or p_data.get("weightInGms") or "N/A"
                brand = p_data.get("brand") or "Unknown"
                
                # URL construction
                slug = p_data.get("slug")
                pvid = p_data.get("id") # Using ID as PVID often works or store_product_id
                url_part = f"/pn/{slug}/pvid/{pvid}" if slug else f"/pvid/{pvid}"
                
                return {
                    "Category": cat_name,
                    "Subcategory": sub_name,
                    "Item Name": name,
                    "Brand": brand,
                    "Mrp": mrp,
                    "Price": price,
                    "Weight/pack_size": str(pack_size),
                    "Delivery ETA": self.delivery_eta,
                    "availability": availability,
                    "inventory": inventory,
                    "store_id": self.store_id,
                    "base_product_id": url_part,
                    "shelf_life_in_hours": str(p_data.get("shelfLifeInHours", "N/A")),
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "pincode_input": pincode,
                    "clicked_label": self.clicked_location_label
                }
            except:
                return None

        # Process all captures
        for capture in captured_data:
            content = capture.get("data")
            
            # CASE 1: JSON Response (API)
            if isinstance(content, dict) or isinstance(content, list):
                # Traverse to find products
                # Usually in props -> pageProps -> initialReduxState -> ... -> products
                # Or simply a list of products in search/category response
                
                # Flatten simple lists
                items_to_check = []
                if isinstance(content, list):
                    items_to_check = content
                elif isinstance(content, dict):
                    # Check common keys
                    if "products" in content: items_to_check.extend(content["products"])
                    if "items" in content: items_to_check.extend(content["items"])
                    # Deep check for storeProducts
                    # This is a naive recursive finder could be better but sticking to known patterns
                    # Let's try to just dump the whole dict values if they look like products
                    pass

                for item in items_to_check:
                    if isinstance(item, dict):
                        p = parse_product_from_dict(item)
                        if p and not any(x['base_product_id'] == p['base_product_id'] for x in products):
                            products.append(p)

            # CASE 2: HTML/String Response (SSR Flight Data)
            if isinstance(content, str) and len(content) > 10000:
                # Regex parsing logic for Flight/HTML string
                # Matches: href="/pn/..." ... >Name</a> ... >Price</td>
                
                # First pass: Build a map of product details from JSON blocks (Inventory, Shelf Life, Pack Size)
                # Key = PVID (id in JSON), Value = dict of attributes
                product_details_map = {}
                try:
                    # Find all "id":"UUID" occurrences in the Flight data (escaped quotes)
                    # We capture a window around it to find other properties
                    # The properties usually follow or precede closely in the same object
                    
                    # Pattern look for id with some context
                    # Flight data is messy, but usually "id" is close to "availableQuantity"
                    # We iterate over all matches of id="UUID"
                    id_matches = re.finditer(r'\\\"id\\\":\\\"([a-f0-9\-]+)\\\"', content)
                    
                    for match in id_matches:
                        pvid_key = match.group(1)
                        start = max(0, match.start() - 1000)
                        end = min(len(content), match.end() + 1000)
                        window = content[start:end]
                        
                        # To ensure we are in the same object, we should ideally parse syntax
                        # But for now, we look for tight proximity or "availableQuantity"
                        # Warning: Window might overlap multiple objects. 
                        # We try to find the "closest" value. 
                        # Actually, looking at debug data, "availableQuantity" comes BEFORE "id" sometimes.
                        # {"availableQuantity":12,"baseProductId":...,"id":"..."}
                        
                        details = {}
                        
                        # Inventory
                        qty_match = re.search(r'\\\"availableQuantity\\\":(\d+)', window)
                        if qty_match: 
                            # Check if this quantity is "closer" to this ID than another?
                            # For now, take it. Most blocks are distinct.
                            details['inventory'] = qty_match.group(1)
                        
                        # Shelf Life
                        sl_match = re.search(r'\\\"shelfLifeInHours\\\":\\\"([^\"]+)\\\"', window)
                        if sl_match: details['shelf_life'] = sl_match.group(1)
                        
                        # Pack Size (raw from store)
                        ps_match = re.search(r'\\\"packsize\\\":(\d+)', window)
                        if ps_match: details['pack_size_raw'] = ps_match.group(1)
                        
                        # Update map
                        if details:
                            if pvid_key not in product_details_map:
                                product_details_map[pvid_key] = {}
                            product_details_map[pvid_key].update(details)
                            
                    logger.info(f"Built details map with {len(product_details_map)} items")
                    
                except Exception as e:
                    logger.warning(f"Error building details map: {e}")

                link_matches = re.finditer(r'href=\"(/pn/[^\"]+)\"', content)
                
                for match in link_matches:
                    try:
                        url_part = match.group(1)
                        if "pvid" not in url_part: continue 
                        
                        start_idx = match.end()
                        snippet = content[start_idx:start_idx+800] 
                        
                        pvid = url_part.split("pvid/")[1] if "pvid/" in url_part else ""
                        
                        # Name
                        name_match = re.search(r'>([^<]+)</a>', snippet)
                        product_name = "Unknown"
                        pack_size = "N/A"
                        brand = "Unknown"
                        price_extracted = None
                        
                        if name_match:
                            raw_name = name_match.group(1).replace("<!-- -->", "").strip()
                            product_name = re.sub(r'^\d+\.\s*', '', raw_name)
                            
                        # Pack Size Regex (from Name)
                        # Matches "500g", "1 kg", "1pc", "Pack of 2"
                        if product_name != "Unknown":
                            size_match = re.search(r'(\d+(?:\.\d+)?\s*(?:g|kg|ml|l|litres|pc|pcs|unit|bunch|pack|bunches)\b)', product_name, re.IGNORECASE)
                            if size_match:
                                pack_size = size_match.group(1)
                                
                        # Brand from URL (Always try this)
                        if "/pn/" in url_part:
                            try:
                                slug = url_part.split("/pn/")[1]
                                brand_slug = slug.split("-")[0]
                                brand = brand_slug.title()
                            except: pass
                            
                        # Refine Brand if " - " exists in Name (overrides slug if valid)
                        if product_name != "Unknown" and " - " in product_name:
                            parts = product_name.split(" - ")
                            if len(parts) > 1 and len(parts[0]) < 20: 
                                    brand = parts[0]

                        # Lookup details
                        inventory = "N/A"
                        shelf_life = "N/A"
                        
                        if pvid in product_details_map:
                            details = product_details_map[pvid]
                            inventory = details.get('inventory', "N/A")
                            shelf_life = details.get('shelf_life', "N/A")
                            
                            # Fallback for pack size if regex failed
                            if pack_size == "N/A" and 'pack_size_raw' in details:
                                pack_size = details['pack_size_raw'] # Might need unit appened, but raw is better than N/A
                        
                        # Price
                        price_match = re.search(r'<td>(₹\d+)</td>', snippet)
                        price = "N/A"
                        if price_match:
                            price = price_match.group(1).replace('₹', '')
                        elif price_extracted:
                            price = str(price_extracted)

                        if not any(p['base_product_id'] == url_part for p in products):
                            item: ProductItem = {
                                "Category": cat_name,
                                "Subcategory": sub_name,
                                "Item Name": product_name,
                                "Brand": brand, 
                                "Mrp": price, 
                                "Price": price,
                                "Weight/pack_size": pack_size,
                                "Delivery ETA": self.delivery_eta,
                                "availability": "In Stock" if inventory != "0" and inventory != "N/A" else "Out of Stock",
                                "inventory": inventory,
                                "store_id": self.store_id,
                                "base_product_id": url_part,
                                "shelf_life_in_hours": shelf_life,
                                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                                "pincode_input": pincode,
                                "clicked_label": self.clicked_location_label
                            }
                            products.append(item)
                    except Exception as e:
                        pass
                        
        logger.info(f"Scraped {len(products)} products from Flight/JSON data")

        return products

    async def scrape_availability(self, product_url: str, pincode: str = "N/A") -> List[ProductItem]:
        logger.info(f"Checking availability for {product_url} at {pincode}")
        products: List[ProductItem] = []
        
        try:
            await self.set_location(pincode)
            
            # Navigate to product page
            await self.page.goto(product_url, timeout=60000)
            await self.human_delay(2)
            
            # We can reuse the same capturing logic or just DOM parsing since it's a single page
            # For speed/simplicity on single page, DOM + Next.js data is often enough
            
            content = await self.page.content()
            
            # Extract Data from NEXT_DATA or similar if possible, or Fallback to DOM
            # Zepto uses standard Next.js often
            
            # DOM Selectors for Product Page
            name = "Unknown"
            try:
                name = await self.page.inner_text("h1")
            except: pass
            
            price = "N/A"
            mrp = "N/A"
            try:
                # Look for price containers
                price_app = await self.page.query_selector("[data-testid='product-price']")
                if price_app:
                     price = await price_app.inner_text()
            except: pass

            try:
                 # MRP usually struck through
                 mrp_el = await self.page.query_selector("[data-testid='product-mrp']")
                 if mrp_el:
                     mrp = await mrp_el.inner_text() 
            except: pass
            
            # Sanitation
            if price != "N/A": price = price.replace("₹", "").strip()
            if mrp != "N/A": mrp = mrp.replace("₹", "").strip()
            
            # Inventory / Add Button
            # If "Add" button exists -> In Stock. If "Out of Stock" text -> Out.
            is_oos = await self.page.query_selector("text=Out of Stock")
            inventory = "10+" # Default if in stock
            if is_oos:
                inventory = "0"
            else:
                 # Check for "Add" button
                 add_btn = await self.page.query_selector("button[aria-label='Add to cart']")
                 if not add_btn:
                     # Maybe it's a counter (already in cart?) or OOS hidden
                     pass
            
            # Weight/Pack Size
            pack_size = "N/A"
            try:
                # Often near title
                ps_el = await self.page.query_selector("[data-testid='product-quantity']")
                if ps_el:
                    pack_size = await ps_el.inner_text()
            except: pass

            item: ProductItem = {
                "Category": "Availability Check",
                "Subcategory": "Direct Link",
                "Item Name": name,
                "Brand": "Unknown", # Could extract
                "Mrp": mrp,
                "Price": price,
                "Weight/pack_size": pack_size,
                "Delivery ETA": self.delivery_eta,
                "availability": "Out of Stock" if inventory == "0" else "In Stock",
                "inventory": inventory,
                "store_id": self.store_id,
                "base_product_id": product_url,
                "shelf_life_in_hours": "N/A",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "pincode_input": pincode,
                "clicked_label": self.clicked_location_label,
            }
            products.append(item)
            
        except Exception as e:
            logger.error(f"Error scraping availability for {product_url}: {e}")
            
        return products

    async def fetch_category_content(self, url: str) -> str:
        """
        Fetches the raw content of a URL using the browser's fetch API.
        This maintains cookies/headers but avoids page rendering overhead.
        """
        try:
            content = await self.page.evaluate(f"""
                async () => {{
                    try {{
                        const response = await fetch("{url}", {{
                            headers: {{
                                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                                'Upgrade-Insecure-Requests': '1'
                            }}
                        }});
                        return await response.text();
                    }} catch (e) {{
                        return null;
                    }}
                }}
            """)
            return content
        except Exception as e:
            logger.error(f"Fast fetch failed for {url}: {e}")
            return None

    async def scrape_assortment_fast(self, category_url: str, pincode: str = None) -> List[ProductItem]:
        """
        Scrapes assortment using network interception to capture React Server Components (RSC) data.
        This is more robust than regex on HTML, ensuring Price, Name, and Inventory are captured.
        """
        logger.info(f"Fast Scraping: {category_url}")
        
        # Extract Category/Sub from URL if possible
        cat_name = "Unknown"
        sub_name = "Unknown"
        try:
            if "/cn/" in category_url:
                parts = category_url.split("/cn/")[1].split("/")
                if len(parts) >= 2:
                    cat_name = parts[0].replace("-", " ").title()
                    sub_name = parts[1].replace("-", " ").title()
        except: pass

        captured_products = {}
        
        # Define capture logic
        async def handle_response(response):
            try:
                ct = response.headers.get("content-type", "")
                if "application/json" in ct or "text/x-component" in ct:
                    text = await response.text()
                    
                    # Optimization: check if line likely contains product data before heavy parsing
                    if '"cardData":' not in text:
                        return

                    # Parse RSC/JSON for products
                    # Strategy: Split by lines (RSC) or just parse JSON
                    lines = text.split('\n')
                    for line in lines:
                        if '"cardData":' in line:
                            # Try to strip RSC prefix (ID:JSON) if present
                            parts = line.split(':', 1)
                            json_part = parts[1] if len(parts) > 1 else line
                                
                            try:
                                data = json.loads(json_part)
                                
                                # Recursive search for cardData
                                def find_cards(obj):
                                    cards = []
                                    if isinstance(obj, dict):
                                        if "cardData" in obj:
                                            cards.append(obj["cardData"])
                                        for k, v in obj.items():
                                            cards.extend(find_cards(v))
                                    elif isinstance(obj, list):
                                        for item in obj:
                                            cards.extend(find_cards(item))
                                    return cards

                                cards = find_cards(data)
                                for card in cards:
                                    if "id" in card:
                                        captured_products[card["id"]] = card
                            except:
                                pass
            except:
                pass

        # Attach listener
        self.page.on("response", handle_response)
        
        try:
            # Navigate
            # Use 'domcontentloaded' or 'networkidle' depending on speed. 
            # networkidle is safer for RSC which streams after load.
            await self.page.goto(category_url, timeout=45000, wait_until='networkidle')
            
            # Small fallback wait to ensure stream completes
            await asyncio.sleep(2)
            
        except Exception as e:
            logger.error(f"Error navigating to {category_url}: {e}")
        finally:
            self.page.remove_listener("response", handle_response)

        # Convert captured data to ProductItem
        products: List[ProductItem] = []
        
        for pid, card in captured_products.items():
            try:
                # Basic Checks
                product_info = card.get('product', {})
                variant_info = card.get('productVariant', {})
                
                name = product_info.get('name')
                if not name: continue 
                    
                # Price (paise -> rupees)
                price = None
                if 'sellingPrice' in card:
                    price = float(card['sellingPrice']) / 100.0
                elif 'discountedSellingPrice' in card:
                    price = float(card['discountedSellingPrice']) / 100.0
                    
                mrp = None
                if 'mrp' in card:
                     mrp = float(card['mrp']) / 100.0
                elif 'mrp' in variant_info:
                     mrp = float(variant_info['mrp']) / 100.0
                     
                inventory = card.get('availableQuantity')
                
                # Format fields
                item: ProductItem = {
                    "Category": cat_name,
                    "Subcategory": sub_name,
                    "Item Name": name,
                    "Brand": product_info.get('brand', "Unknown"),
                    "Mrp": mrp if mrp is not None else "N/A",
                    "Price": price if price is not None else "N/A",
                    "Weight/pack_size": variant_info.get('formattedPacksize', "N/A"),
                    "Delivery ETA": self.delivery_eta,
                    "availability": "In Stock" if (inventory and inventory > 0) else "Out of Stock",
                    "inventory": inventory if inventory is not None else "0",
                    "store_id": card.get('storeId', self.store_id),
                    "base_product_id": pid,
                    "shelf_life_in_hours": variant_info.get('shelfLifeInHours', "N/A"),
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "pincode_input": pincode,
                    "clicked_label": self.clicked_location_label
                }
                products.append(item)
            except Exception as e:
                 # logger.warning(f"Failed to parse product card: {e}")
                 pass

        logger.info(f"Fast scraped {len(products)} products from {category_url}")
        return products


