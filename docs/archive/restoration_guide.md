# Removed Files Log & Restoration Guide

The following files were removed from the `c:\scrapers\scraper_zepto` directory to clean up the project for professional delivery. 
If you need to restore any of these functionalities, you can recreate the files using the descriptions below or retrieve them from a previous backup.

## Debugging Scripts
These scripts were used for development testing and debugging specific components.

| File Name | Purpose |
| :--- | :--- |
| `analyze_flight_data.py` | Analyzed raw flight dump text files to understand network traffic patterns. |
| `analyze_json.py` | Parsed and analyzed structure of captured JSON responses. |
| `analyze_rsc.py` | Analyzed React Server Component (RSC) payloads. |
| `analyze_rsc_v2.py` | Improved version of RSC payload analysis. |
| `debug_categories.py` | Tested category extraction logic specifically. |
| `debug_fast_fetch.py` | POC for testing fast API fetching capabilities. |
| `debug_fields.py` | Inspected specific data fields in scraper output. |
| `debug_html.py` | Dumped and inspected raw HTML content. |
| `debug_modal.py` | Debugged the location selection modal interactions. |
| `debug_zepto.py` | General debugging script for the main Zepto scraper class. |
| `debug_zepto_json.py` | Validated JSON parsing logic. |
| `fetch_debug_data.py` | Helper to fetch data for debugging purposes. |
| `inspect_debug_data.py` | Script to inspect the contents of debug data files. |
| `inspect_debug_html.py` | Script to search for selectors in dumped HTML. |
| `inspect_fields.py` | Utility to list all fields found in scraped data. |
| `inspect_product_context.py` | Analyzed product context data from web pages. |
| `inspect_slug.py` | Debugged URL slug generation/parsing. |
| `parse_flight_dump.py` | Parser for raw network flight logs. |

## Verification Scripts
Scripts used to verify fixes and integrity during development.

| File Name | Purpose |
| :--- | :--- |
| `verify_clicked_label.py` | **Recently Removed**: Verified that the address label was correctly captured. |
| `verify_fix.py` | Verified a specific ephemeral fix. |
| `verify_ids.py` | Checked for uniqueness of IDs in dataset. |
| `verify_imports.py` | Checked if all python imports were working correctly. |

## Temporary Data Dumps
Raw data captured during debugging sessions.

| Filename Pattern | Description |
| :--- | :--- |
| `api_dump.json` | Full dump of API response data. |
| `debug_*.json` | Various debug JSON outputs (e.g., `debug_api_responses.json`). |
| `debug_*.html` | Snapshot of HTML pages (e.g., `debug_homepage.html`). |
| `debug_*.png` | Screenshots taken during scraper execution for debugging. |
| `debug_*.txt` | Text dumps of logs or intermediate data. |
| `flight_dump_*.txt` | Raw network logs from specific requests. |
| `performance_metrics.json` | Intermediate performance stats (final report is in CSV). |

## Logic for Removal
- **Professionalism**: Client deliverables should only contain the source code (`scrapers/`, `dashboard/`), essential runners (`run_*.py`), configuration (`requirements.txt`), and documentation.
- **Size**: Debug dumps can be large and clutter the repository.
- **Security**: Removing temp dumps prevents accidental sharing of PII or session data.
