# Wine Data Toolkit

A collection of Python tools for fetching wine data from Vivino, uploading to Algolia, and enriching it with AI-generated insights.

## Project Overview

This repository contains tools to:

1. **Fetch wine data** from Vivino's API (vivino-api.py)
2. **Upload wine data** to Algolia for search functionality (algolia_vivino_index_upload.py)
3. **Enrich wine data** with AI-generated insights using Algolia's GenAI Toolkit (algolia-genai-wine-enrichment.py)

## Repository Structure

```
wine-data-toolkit/
├── src/
│   ├── vivino-api.py               # Script to fetch wine data from Vivino
│   ├── algolia_vivino_index_upload.py  # Script to upload wine data to Algolia
│   └── algolia-genai-wine-enrichment.py # Script to enrich data with AI insights
├── .gitignore                      # Specifies files to ignore in Git
├── LICENSE                         # License information
├── README.md                       # This file
└── requirements.txt                # Python dependencies
```

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/wine-data-toolkit.git
   cd wine-data-toolkit
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up your Algolia account:
   - Create an account at [Algolia](https://www.algolia.com/)
   - Get your Application ID and API Key from the Algolia dashboard

## Usage

### 1. Fetch Wine Data from Vivino

```bash
python src/vivino-api.py
```

This will prompt you for the number of wines to collect and save the data to JSON and CSV files.

### 2. Upload Wine Data to Algolia

```bash
python src/algolia_vivino_index_upload.py --app-id YOUR_APP_ID --api-key YOUR_API_KEY --index-name your_index_name --file path/to/vivino_wines.json
```

### 3. Enrich Wine Data with AI Insights

```bash
python src/algolia-genai-wine-enrichment.py --app-id YOUR_APP_ID --api-key YOUR_API_KEY --source-index your_index_name --target-index enriched_index_name
```

## Required API Keys

- **Algolia**: You'll need an Application ID and API Key from your Algolia account

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.