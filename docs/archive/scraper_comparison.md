# Scraper Comparison: Zepto vs Blinkit

This document compares the current implementation of the Zepto and Blinkit scrapers based on code analysis.

| Feature | Zepto Scraper (`scraper_zepto`) | Blinkit Scraper (`scraper_blinkit`) | Winner |
| :--- | :--- | :--- | :--- |
| **Scraping Strategy** | **Turbo Mode (API Fetch)**<br>Uses `page.evaluate(fetch)` to execute API calls directly from the browser context. No page rendering. | **Parallel Tabs**<br>Opens multiple browser tabs (`context.new_page()`) to load category pages concurrently. | **Zepto** (Faster & Lighter) |
| **Speed** | **~0.1s - 0.5s per category**<br>Milliseconds latency. Limited only by network. | **~2s - 5s per category**<br>Requires DOM initialization, even with resource blocking. | **Zepto** |
| **Resource Usage** | **Low**<br>Single tab per worker. Minimal CPU/RAM. | **High**<br>Multiple tabs per worker. High RAM usage (Chromium processes). | **Zepto** |
| **Architecture** | **Async Producer-Consumer**<br>Workers + Dedicated Writer Task. | **Async Producer-Consumer**<br>Workers + Dedicated Writer Task. | **Tie** |
| **Data Extraction** | **Robust JSON/Flight Parsing**<br>Handles Zepto's complex "Flight" data and standard JSON. | **NEXT_DATA / DOM**<br>Extracts from `__NEXT_DATA__` script tag or falls back to Regex/DOM. | **Tie** (Both optimized for target) |
| **Location Setting** | **Standard**<br>Sets location once per worker session. | **Robust with Retry**<br>Includes complex retry logic for location triggers and modal interaction. | **Blinkit** (Slightly more defensive) |
| **Anti-Bot** | **Natural Cookies**<br>Reuses browser session cookies for API calls. | **Resource Blocking**<br>Blocks images/fonts to reduce footprint and speed up load. | **Zepto** (Stealthier) |

## Tech Deep Dive

### Zepto (The "Turbo" Approach)
The Zepto scraper has been upgraded to a **"Headless Browser API Relay"** pattern.
1.  **Auth**: It uses the browser *only* to establish a valid session (cookies, tokens, location).
2.  **Fetch**: It then injects JavaScript to use the browser's own `fetch()` function.
3.  **Benefit**: This bypasses the visual rendering engine (Layout, Paint) completely, which is the slowest part of modern web scraping. It makes the scraper behave like a lightweight API client but with the perfect trust score of a real browser.

### Blinkit (The "Multi-Tab" Approach)
The Blinkit scraper uses a **"Concurrent Browser Context"** pattern.
1.  **Isolation**: It opens independent tabs for categories.
2.  **Concurrency**: It sets `concurrency=4` (semaphores) to load 4 pages at once per worker.
3.  **Drawback**: Even with `await route.abort()` blocking images, Chrome still has to initialize the DOM execution environment for every tab, which consumes significant memory and CPU.

## Recommendation
**Upgrade Blinkit to Turbo Mode**: The Blinkit scraper logic could be refactored to use the same `fetch` strategy as Zepto. Since Blinkit also uses Next.js (evidenced by `__NEXT_DATA__`), it likely has a clean internal API that can be queried directly, or the page HTML can be fetched as a string without full rendering.
