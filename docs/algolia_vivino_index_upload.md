# Algolia Vivino Index Uploader

A Python script to upload wine data to Algolia for enhanced search capabilities.

## Overview

This script takes wine data collected from Vivino and uploads it to Algolia's search platform. It handles:

- Preparing wine data for optimal search performance
- Creating and configuring Algolia indices with appropriate settings
- Uploading data in batches with retry logic for reliability
- Cleaning and formatting wine attributes for faceting and filtering

## Features

- Clears existing index data (optional)
- Configures optimal search settings for wine data
- Creates price ranges for faceting
- Handles batch uploading with retry logic and exponential backoff
- Provides checkpointing for resumable uploads
- Offers progress tracking with tqdm

## Requirements

- Python 3.6+
- algoliasearch
- tqdm
- json

## Usage

```bash
python algolia_vivino_index_upload.py --app-id YOUR_APP_ID --api-key YOUR_API_KEY --index-name your_index_name --file path/to/vivino_wines.json
```

### Arguments

- `--app-id` (required): Your Algolia Application ID
- `--api-key` (required): Your Algolia Admin API Key
- `--index-name` (required): The name of the Algolia index to use
- `--file`: Path to the JSON file with wine data (default: looks in vivino_wine_data directory)
- `--batch-size`: Number of records per batch (default: 250)
- `--skip-clear`: Skip clearing the index before uploading
- `--resume`: Resume from last checkpoint (only works with --skip-clear)

## Index Configuration

The script configures the Algolia index with the following settings:

- **Searchable Attributes** (in order of importance):
  - name
  - winery_name
  - grape_names
  - region_name
  - country_name
  - type_name
  - style_name

- **Faceting Attributes**:
  - type_name
  - country_name
  - region_name
  - grape_names (searchable)
  - winery_name (searchable)
  - year
  - price_range

- **Custom Ranking**:
  - desc(average_rating)
  - desc(ratings_count)

## Example Output

```
===== Algolia Clean & Reindex Script =====

Settings:
  Algolia App ID:   your_app_id
  Algolia Index:    vivino_wines
  Data File:        vivino_wine_data/vivino_wines_final_5000.json
  Batch Size:       250
  Skip Clear:       False
  Resume Upload:    False

Initializing Algolia client...
Connecting to Algolia with app_id: your_app_id
Found index 'vivino_wines' with approximately 5000 records
Clearing all records from index 'vivino_wines'...
Successfully cleared all records from index 'vivino_wines'
Configuring index settings...
Index configuration complete
Loading JSON file: vivino_wine_data/vivino_wines_final_5000.json
Successfully loaded JSON with 5000 records
Preparing 5000 wines for Algolia...
Prepared 5000 wines for upload (0 skipped)
Uploading 5000 wines to Algolia in 20 batches...
Using batch size of 250 records
```