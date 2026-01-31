# Dashboard Comparison: Blinkit vs Zepto

After analyzing the source code of both dashboards, the following discrepancies were found. The Zepto dashboard is missing key interactive features present in the Blinkit version.

## Missing Features in Zepto Dashboard

### 1. Scraper Controls & Automation
The most significant missing section is the **Scraper Controls** in the sidebar.
- **File Uploaders**: The Blinkit dashboard allows users to upload Excel files for input (`pin_codes.xlsx` for assortment, `pin_codes_100.xlsx` for availability).
- **Execution Buttons**: The Blinkit dashboard has buttons to trigger the scraper scripts (`run_blinkit_assortment_parallel.py`, `run_blinkit_parallel.py`) directly from the UI using `subprocess`.
- **Mode Selection**: The Blinkit dashboard allows switching between "Assortment" and "Availability" modes.

**Code Missing in Zepto:**
```python
# Mode Selection
scrape_mode = st.sidebar.radio("Select Scrape Mode", ["Assortment (All Categories)", "Availability (Specific Links)"])

if scrape_mode == "Assortment (All Categories)":
    uploaded_file = st.sidebar.file_uploader(...)
    # ... file saving logic ...
    if st.sidebar.button("Run Assortment Scraper"):
        subprocess.Popen(...)
```

### 2. Database Upload Time Filter
- **Blinkit**: Includes a sidebar filter for `created_at` timestamps ("Select DB Upload Time"), allowing users to see when batches were uploaded to the database, not just when they were scraped.
- **Zepto**: Only has the "Select Scrape Time" filter.

### 3. Date Processing
- **Blinkit**: Processes both `scraped_at` and `created_at` columns.
- **Zepto**: Only processes `scraped_at`.

## Summary Table

| Feature | Blinkit | Zepto |
| :--- | :--- | :--- |
| **Visualize Data** | ✅ Yes | ✅ Yes |
| **Time Filters** | ✅ Scraped & Upload Time | ⚠️ Scraped Time Only |
| **Pincode Input** | ✅ File Upload (UI) | ❌ Manual Command Line |
| **Run Scraper** | ✅ One-Click Button | ❌ Manual Command Line |
| **Scrape Modes** | ✅ Assortment & Availability | ❌ Assortment Only (Implicit) |

## Recommendation
To bring the Zepto dashboard to parity:
1.  Import `subprocess` and `os` in `app.py`.
2.  Add the Sidebar "Scraper Controls" section.
3.  Implement the file uploader for Zepto's input file (if applicable).
4.  Add buttons to trigger `run_zepto.py` (or a parallel equivalent if it exists).
5.  Update the data loading logic to parse `created_at` if that column is available in the `zepto_assortment` table.
