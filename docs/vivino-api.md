# Vivino API Scraper

A Python script to fetch wine data from Vivino's API.

## Overview

This script allows you to collect wine data from Vivino using their API. It fetches information about wines including:

- Basic wine details (name, year, type)
- Winery information
- Region and country
- Ratings and reviews
- Price information
- Grape varieties
- Taste profiles
- Food pairings

## Features

- Collects wine data from multiple categories (red, white, sparkling, etc.)
- Fetches data from various regions and countries
- Filters for wines with specific ratings
- Saves data in both JSON and CSV formats
- Implements random delays to avoid rate limiting
- Shows progress with tqdm progress bars

## Requirements

- Python 3.6+
- requests
- json
- csv
- tqdm

## Usage

```bash
python vivino-api.py
```

The script will prompt you for the number of wines to collect. Enter a number or 'all' for comprehensive collection.

### Customization

You can modify these variables in the script to customize data collection:

- `max_wines`: Maximum total wines to collect
- `wines_per_query`: How many wines to collect per query/category
- `save_interval`: How often to save progress

## Output

The script creates a `vivino_wine_data` directory with:

- JSON files containing the complete wine data
- CSV files with the same data in tabular format

Both checkpoints and final datasets are saved with timestamps.

## Example Output

```
Starting comprehensive Vivino wine data collection (target: 1000 wines)...
Using 54 different search strategies

Strategy 1/54: Wines of cabernet sauvignon
Target: Collect up to 200 wines from this category
  Fetching page 1...
  Found 50 wines on page 1
  Added 50 new wines from page 1
  Progress: 50/200 for this strategy, 50/1000 overall
  ...
```