# Dashboard Modes Explanation

This document explains the two "Bulk" execution modes available in the Zepto Streamlit Dashboard.

## 1. Bulk Assortment (File)
**Goal**: Discover and scrape **every product** available in a location.

- **Input**: An Excel file (`pin_codes.xlsx`) containing a column of Pincodes.
- **Process**:
  1.  The scraper reads each pincode from the file.
  2.  For each pincode, it visits the Zepto homepage and extracts **all** category links (Grocery, Fruits, Snacks, etc.).
  3.  It navigates to every category page and scrapes the full list of products.
- **Output**: A comprehensive dataset of the entire store catalog for those locations.
- **Use Case**: "I want to see everything Zepto sells in Bangalore vs. Mumbai."

## 2. Bulk Availability (File)
**Goal**: Check the stock status of **specific items** you already know about.

- **Input**: An Excel file (`pin_codes_100.xlsx`) containing two columns: `url` (Product Link) and `pincode`.
- **Process**:
  1.  The scraper reads the specific pairs of Product URL + Pincode.
  2.  It navigates **directly** to that product page.
  3.  It extracts the current Price, MRP, and Inventory status (In Stock/Out of Stock).
- **Output**: A targeted status report for the specific items you requested.
- **Use Case**: "I want to track if 'Amul Butter 500g' is in stock across 50 different pincodes right now."
