# Zalando Product Monitor

A simple product monitor for Zalando that fetches and parses product information from Zalando product pages.



## Installation

### Requirements
- Python 3.7+
- pip

### Dependencies

```bash
pip install requests beautifulsoup4 urllib3
```

## Usage

```bash
python main.py
```

## Output

The script generates a JSON file with the following structure:

```json
{
  "url": "https://www.zalando.dk/...",
  "fetched_at": "2024-01-15T10:30:45.123456",
  "product_name": "Samba OG",
  "brand": "Adidas",
  "price": "899,95 kr",
  "available_sizes": ["36", "37", "38", "39"],
  "all_sizes": ["36", "37", "38", "39", "40"],
  "images": ["https://...", "https://..."],
  "product_id": "ad115o1rq",
  "color": "Brown",
  "in_stock": true,
  "stock_status": "In Stock"
}
```

## Classes

### ZalandoMonitor

Main class for product monitoring.

**Methods:**
- `__init__(product_url)` - Initializes the monitor with product URL
- `fetch_product_page()` - Fetches HTML content from the product page
- `parse_product_data(html_content)` - Parses HTML and extracts product data
- `monitor()` - Runs full monitoring cycle
- `save_to_json(filename)` - Saves product data to JSON file

## Features

- **Robust HTTP Handling**: Retry logic with exponential backoff
- **Mobile User-Agent**: Uses iPhone User-Agent for better compatibility
- **Logging**: Detailed logging of all operations
- **Error Tolerance**: Graceful degradation on parsing errors

## Logging

The script uses Python's `logging` module. Log output is displayed in the console with the following format:

```
2024-01-15 10:30:45,123 - INFO - Fetching: https://www.zalando.dk/...
2024-01-15 10:30:46,456 - INFO - Status: 200
```



