# Zepto Scraper & Dashboard

A professional, asynchronous web scraper for Zepto (grocery delivery) with a real-time analytics dashboard. Built with Python, Playwright, Supabase, and Streamlit.

## Features

- **High-Performance Scraping**: Async architecture using `playwright` for fast, parallel data extraction.
- **Intelligent Location Handling**: Automatically handles location selection and pincode inputs.
- **Robustness**: Handles anti-bot measures, network interception for RSC (React Server Components), and DOM fallbacks.
- **Data Pipeline**: 
    - Extracts products, prices, inventory, and delivery ETAs.
    - Saves data to CSV and automatically uploads to Supabase.
- **Analytics Dashboard**: Streamlit-based dashboard to visualize pricing trends, availability, and assortment gaps.

## Project Structure

```text
├── src/
│   ├── scrapers/          # Core scraping logic (ZeptoScraper)
│   ├── dashboard/         # Streamlit analytics dashboard
│   ├── database.py        # Database connection layer
│   └── schema.sql         # Database schema
├── scripts/               # Entry points for running scrapers
│   ├── run_zepto.py       # Single instance runner
│   ├── run_parallel.py    # Parallel execution script
│   └── ...
├── data/
│   ├── input/             # Pincode lists and config files
│   └── output/            # Scraped CSVs and performance reports
└── docs/                  # Documentation
```

## Setup

1. **Clone the repository**
   ```bash
   git clone <repo_url>
   cd scraper_zepto
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   playwright install
   ```

3. **Configuration**
   - Copy `.env.example` to `.env` and fill in your Supabase credentials.
   ```bash
   cp .env.example .env
   ```

4. **Prepare Data**
   - Place your pincode list (Excel file) in `data/input/`.

## Usage

### Running the Scraper
To run the scraper for multiple pincodes in parallel:
```bash
python scripts/run_zepto_assortment_parallel.py
```
Outputs will be saved to `data/output/`.

### Running the Dashboard
To view the analytics dashboard:
```bash
streamlit run src/dashboard/app_zepto.py
```

## Tech Stack
- **Python 3.10+**
- **Playwright** (Browser Automation)
- **Pandas** (Data Processing)
- **Supabase** (PostgreSQL Database)
- **Streamlit** (UI/Dashboard)

## License
[MIT](LICENSE)
