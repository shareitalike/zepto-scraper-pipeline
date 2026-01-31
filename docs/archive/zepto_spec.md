# Zepto Scraper Specification

## 1. Overview
The Zepto Scraper is a specialized tool designed to extract product assortment, pricing, availability, and delivery information from [Zepto](https://www.zepto.com/). It operates by automating a headless browser to simulate user interactions (setting location, navigating categories) and intercepting network traffic to capture rich data payloads.

## 2. Architecture
The scraper is built in Python using `playwright` for browser automation and `pandas` for data handling.

- **Base Class**: `BaseScraper` (`scrapers/base.py`)
  - **Responsibility**: Manages the Playwright browser session, context, and page lifecycle.
  - **Stealth**: Implements anti-detection measures (custom headers, removing `navigator.webdriver`, random human-like delays/scrolling).
  - **Abstract Methods**: Defines `set_location` as a required implementation.

- **Main Class**: `ZeptoScraper` (`scrapers/zepto.py`)
  - **Inheritance**: Inherits from `BaseScraper`.
  - **Responsibility**: Implements Zepto-specific logic for location setting, category discovery, and data extraction.

- **Runner**: `run_zepto.py`
  - **Responsibility**: Command-line entry point. Handles argument parsing (pincode), orchestration of the scraping flow, and saving results to CSV.

## 3. Workflow

### 3.1 Initialization
- The scraper launches a Chromium-based browser (trying Edge, Chrome, then bundled Chromium).
- It configures a "stealth" context with a standard User-Agent and modified navigator properties to avoid bot detection.

### 3.2 Location Setting (`set_location`)
1.  **Navigation**: Goes to `https://www.zepto.com/`.
2.  **Trigger**: Detects and clicks the "Select Location" button (handling both standard and JS-forced clicks).
3.  **Input**: Waits for the address modal/input to appear.
4.  **Entry**: Clears any existing text and types the provided **Pincode** with human-like typing delays (100ms/char).
5.  **Selection**: Presses `Enter` and selects the first prediction result from the dropdown.
6.  **Metadata Extraction**: 
    - Captures **Delivery ETA** (e.g., "10 mins") from the UI or regex fallback.
    - Captures **Store ID** from the page source using regex (`storeId":"..."`).

### 3.3 Category Discovery (`get_all_categories`)
- Scans the homepage for navigation links.
- Filters for URLs containing `/cn/` (Category Name) and `/cid/` (Category ID).
- Returns a list of unique category URLs to process.

### 3.4 Assortment Scraping (`scrape_assortment`)
For each category URL:
1.  **Navigation**: Navigates to the category page.
2.  **Interception**: Sets up a network response listener to capture all incoming HTTP responses.
    - **Filter**: Ignores images, fonts, CSS. Captures JSON and large Text/HTML responses.
3.  **Data Loading**: Performs "human scrolling" (scroll down/up) to trigger lazy-loading of products and additional API calls.
4.  **Data Parsing**:
    - **Source**: Primarily parses "Flight" data (Server-Side Rendered state) or API JSON responses embedded in the page or returned by network requests.
    - **Detail Mapping**: Builds a dictionary of product details (Inventory, Shelf Life, Pack Size) by regex-searching the raw response content for `id`, `availableQuantity`, `shelfLifeInHours`, etc.
    - **Product Extraction**:
        - Iterates through product links (`/pn/...`).
        - **Name**: Extracted from HTML anchor tags.
        - **Brand**: Extracted from the URL slug or parsed from the product name.
        - **Price**: Extracted from HTML table cells (`<td>₹...</td>`) or regex.
        - **Pack Size**: Parsed via regex from the product Name (e.g., "500g", "1 pack") or looked up in the detail map.
        - **Availability**: Determined by `inventory` count (if > 0 then In Stock).
        - **Metadata**: Adds Store ID, ETA, Timestamp, Pincode.

## 4. Data Model
The scraper outputs a list of dictionaries (saved as CSV). Key fields include:

| Field | Description | Source |
| :--- | :--- | :--- |
| `Category` | Category Name | Derived from URL |
| `Subcategory` | Subcategory Name | Derived from URL |
| `Item Name` | Product Title | HTML/Regex |
| `Brand` | Brand Name | URL Slug or Name parsing |
| `Mrp` | Maximum Retail Price | HTML/Regex |
| `Price` | Selling Price | HTML/Regex |
| `Weight/pack_size` | Quantity (e.g. 500g) | Regex from Name or Detail Map |
| `Delivery ETA` | est. delivery time | Header UI |
| `availability` | "In Stock" / "Out of Stock" | Derived from Inventory |
| `inventory` | Exact stock count | JSON/Regex |
| `store_id` | Zepto Store UUID | Page Source Regex |
| `base_product_id` | URL Slug/ID | URL |
| `shelf_life_in_hours` | Product Shelf Life | JSON/Regex |
| `pincode_input` | Input Pincode | User Argument |

## 5. Key Technical Features
- **Hybrid Parsing**: Uses both DOM selectors (for ETA, basic interaction) and Raw Response/Regex parsing (for rich product data hidden in JSON blobs).
- **Resilience**: Includes multiple fallback strategies for finding elements (e.g., multiple selectors for search input, regex backup for ETA).
- **Stealth**: Random delays and pointer movements mimic human behavior to reduce blocking risk.

## 6. Usage
Run via command line:
```bash
python run_zepto.py --pincode 560001
```
This will generate `zepto_products_560001.csv` containing the scraped data.
