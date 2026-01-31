# Implementation Plan - Zepto Bulk & Availability Scraping

The goal is to upgrade the Zepto scraper to support **Bulk Assortment Scraping** (via Pincode Excel) and **Availability Scraping** (via Link/Pincode Excel), and expose these options in the Streamlit dashboard.

## User Review Required
> [!NOTE]
> This requires creating new parallel execution scripts and modifying the core scraper to support direct product URL scraping.

## Proposed Changes

### 1. Core Scraper (`scrapers/zepto.py`)
#### [MODIFY] [zepto.py](file:///c:/scrapers/scraper_zepto/scrapers/zepto.py)
- **New Method**: `scrape_availability(self, product_url: str, pincode: str)`
    - Navigates to the product URL.
    - Sets location if not already set.
    - Extracts Price, MRP, Inventory, Availability, Store ID, etc. from "Flight" data or DOM.

### 2. Parallel Runners (New Files)
#### [NEW] `run_zepto_assortment_parallel.py`
- Adapts Blinkit's parallel runner.
- **Input**: `pin_codes.xlsx`
- **Logic**: Reads pincodes, spawns multiple `ZeptoScraper` instances (simulated or actual parallel processes), scrapes all categories, saves to `zepto_assortment_parallel.csv`.

#### [NEW] `run_zepto_availability_parallel.py`
- **Input**: `pin_codes_100.xlsx` (Columns: `url`, `pincode`)
- **Logic**: Reads URL/Pincode pairs, scrapes specific products, saves to `zepto_availability.csv`.

### 3. Dashboard (`dashboard/app_zepto.py`)
#### [MODIFY] [app_zepto.py](file:///c:/scrapers/scraper_zepto/dashboard/app_zepto.py)
- **UI Update**:
    - Add **Radio Button**: "Scrape Mode" -> ["Assortment (Bulk)", "Availability (Links)"].
    - **Assortment Mode**:
        - File Uploader for `pin_codes.xlsx`.
        - "Run Assortment Scraper" button (triggers `run_zepto_assortment_parallel.py`).
    - **Availability Mode**:
        - File Uploader for `pin_codes_100.xlsx`.
        - "Run Availability Scraper" button (triggers `run_zepto_availability_parallel.py`).

## Verification Plan
1.  **Test Availability Logic**: Create a small script to test `scrape_availability` with one URL.
2.  **Test Parallel Runners**: Run with a small input file (1-2 pincodes/links).
3.  **Test Dashboard**: Verify file uploads and button triggers work.
