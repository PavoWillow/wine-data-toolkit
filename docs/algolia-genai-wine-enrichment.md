# Algolia GenAI Wine Enrichment

A Python script to enrich wine data with AI-generated insights using Algolia's GenAI Toolkit.

## Overview

This script takes wine data stored in an Algolia index and enriches it with AI-generated insights. It creates multiple types of wine-specific analysis including taste profiles, soil characteristics, quality assessments, and sommelier descriptions.

## Features

- Creates AI-powered data enrichment for wine records
- Generates multiple types of wine analysis:
  - Taste profiles (primary, secondary, tertiary tastes)
  - Soil profiles
  - Quality assessments
  - Sommelier descriptions
  - Weather/climate information
  - Cultural and historical context
  - Value assessments
  - Serving recommendations
- Processes wines in parallel for efficiency
- Handles rate limiting with backoff strategies
- Supports listing and managing Algolia GenAI resources

## Requirements

- Python 3.6+
- algoliasearch
- requests
- tqdm
- concurrent.futures (standard library)

## Usage

```bash
python algolia-genai-wine-enrichment.py --app-id YOUR_APP_ID --api-key YOUR_API_KEY --source-index source_index_name --target-index target_index_name
```

### Arguments

- `--app-id` (required): Your Algolia Application ID
- `--api-key` (required): Your Algolia API Key
- `--source-index` (required): Source Algolia index name containing wine data
- `--target-index`: Target Algolia index for storing enriched data (default: same as source)
- `--genai-region`: Algolia GenAI Toolkit region ('us' or 'eu', default: 'us')
- `--batch-size`: Number of wines to process in each batch (default: 10)
- `--max-workers`: Maximum number of parallel workers (default: 2)
- `--limit`: Maximum number of wines to process, 0 for all (default: 0)
- `--filter`: Algolia filter query to select specific wines
- `--enrichment-types`: List of specific enrichment types to perform

### Listing Operations

The script also supports listing Algolia GenAI resources:

```bash
python algolia-genai-wine-enrichment.py --app-id YOUR_APP_ID --api-key YOUR_API_KEY --list-data-sources
```

Available listing commands:
- `--list-data-sources`: List all data sources
- `--list-prompts`: List all prompts
- `--list-responses`: List all responses
- `--list-conversations`: List all conversations
- `--output-format`: Output format ('json' or 'table', default: 'table')
- `--output-file`: Save listing output to a file

## Enrichment Types

The script can generate the following types of wine analysis:

1. **Taste Profile**: Analyzes primary, secondary, and tertiary taste characteristics
2. **Soil Profile**: Provides information about soil types and characteristics from the wine's region
3. **Quality Assessment**: Evaluates balance, intensity, clarity, complexity, and typicity
4. **Sommelier Description**: Creates professional wine descriptions with food pairings
5. **Weather Profile**: Analyzes climate and weather influences
6. **Cultural & Historical Context**: Provides winery history and regional traditions
7. **Value Assessment**: Evaluates price-to-quality ratio
8. **Serving Conditions**: Recommends temperature, decanting, glassware, etc.

## Example Output

```
=== Algolia GenAI Wine Enrichment ===
Source Index: vivino_wines
Target Index: enriched_vivino_wines
GenAI Region: us
Batch Size: 10
Max Workers: 2
Limit: 50
Filter: None
Enrichment Types: taste_profile, soil_profile, quality_assessment, sommelier_description
=====================================

Setting up data sources...
Successfully created data source: All Wines
Successfully created data source: Red Wines
Successfully created data source: White Wines
Setting up prompts...
Successfully created prompt: Wine Taste Profile Analysis
Successfully created prompt: Wine Soil Profile Analysis
...
```