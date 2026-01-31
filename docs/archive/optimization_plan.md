# Optimization Plan: Zepto Turbo Mode

**Goal**: Scrape 100 pincodes in 30 minutes (~250,000 items).
**Current Speed**: ~215 items/min.
**Target Speed**: ~8,300 items/min (40x Speedup).

## bottlenecks
1.  **Page Load**: Loading HTML/CSS/Images for 55 categories per pincode takes ~20 minutes.
2.  **Sequential Navigation**: We visit pages one by one.

## Solution: In-Browser API Replay ("Turbo Mode")
Instead of navigating to category pages, we will:
1.  **Navigate Once**: Open Homepage & Set Location (Validates Auth/Cookies).
2.  **Extract Context**: Capture `latitude`, `longitude`, and `storeId` from network traffic during location set.
3.  **Parallel Fetch**: Use `page.evaluate()` to execute JavaScript `fetch()` calls directly to Zepto's backend API (`bff-gateway`).
    -   This reuses the browser's valid cookies/headers.
    -   We can batch 10-20 categories in parallel.
    -   No page rendering = milliseconds response time.

## Proposed Changes

### 1. `ZeptoScraper` modification
#### [MODIFY] `scrapers/zepto.py`
-   Add `self.location_data` to store lat/long/store_id.
-   Add `fetch_category_api(self, category_id, page_params)` method.
-   Create `scrape_assortment_fast(self)`:
    -   Gets all category IDs.
    -   Constructs API URLs.
    -   Runs `Promise.all(fetches)` in browser context.
    -   Parses JSON directly.

### 2. Parallel Runner Update
#### [MODIFY] `run_zepto_assortment_parallel.py`
-   Increase `MAX_WORKERS` to 8-10 (since browser load will be lower).
-   Switch to calling `scrape_assortment_fast`.

## Verification
-   Create `poc_fast_fetch.py` to prove we can manually `fetch()` the API from console.
