# Wine Data Toolkit

A comprehensive suite of tools for wine enthusiasts, developers, and businesses to collect, enrich, and interact with detailed wine data through AI-powered interfaces.

## 🍷 Project Overview

The Wine Data Toolkit represents a complete data pipeline and AI application system for wine data:

1. **Data Collection**: Crawl Vivino's website to gather detailed information about thousands of wines
2. **Data Storage**: Upload and index the wine data in Algolia for powerful search capabilities
3. **Data Enrichment**: Use Algolia's GenAI Toolkit to enrich wine data with AI-generated insights
4. **Interactive AI Interface**: Engage with the data through a sophisticated AI Sommelier assistant with web-based chat interface and analytics

This project demonstrates the full lifecycle of building an AI-powered application - from data gathering to intelligent user interface.

## 🔍 Components

### 1. Data Collection (Vivino Crawler)

A Python script that crawls Vivino's wine database to collect information such as:

- Wine names, vintages, and types
- Winery information and regions
- Ratings and reviews
- Pricing data
- Grape varieties
- Tasting notes

The crawler intelligently navigates Vivino's website to gather a comprehensive dataset of wines from around the world.

### 2. Algolia Indexing

Once the data is collected, it's uploaded to Algolia's search platform, providing:

- Lightning-fast search capabilities
- Complex filtering options
- Typo tolerance
- Customized ranking

This process transforms raw wine data into a structured, searchable index that powers all subsequent components.

### 3. AI-Powered Data Enrichment

Using Algolia's GenAI Toolkit, the wine data is enriched with AI-generated attributes such as:

- Detailed taste profiles (primary, secondary, and tertiary notes)
- Food pairing suggestions
- Quality assessments
- Aging potential
- Value ratings
- Detailed tasting instructions

This transforms factual wine data into rich, insightful information that enhances the end-user experience.

### 4. Sommelier AI Assistant

The crown jewel of the toolkit - an interactive AI sommelier that can:

- Provide personalized wine recommendations based on preferences
- Offer detailed food and wine pairing suggestions
- Educate users about wine regions, grape varieties, and tasting techniques
- Guide users through wine selection for specific occasions
- Share interesting facts and stories about wineries and vineyards

Features include:
- **Web-based Chat Interface**: Elegant UI for interacting with the sommelier
- **Smart Caching System**: Improves performance and reduces costs by caching responses
- **Real-time Analytics Dashboard**: Monitors cache performance, response times, and cost savings
- **Multiple Specialized Prompts**: Tailored AI behavior for different query types (recommendations, education, pairings)

## 📂 Repository Structure

```
wine-data-toolkit/
├── src/
│   ├── vivino-api.py               # Script to fetch wine data from Vivino
│   ├── algolia_vivino_index_upload.py  # Upload wine data to Algolia
│   ├── algolia-genai-wine-enrichment.py # Enrich data with AI insights
│   └── sommelier/                  # Sommelier AI Assistant
│       ├── sommelier_ai_assistant.py    # Core sommelier functionality with metrics
│       ├── app.py                  # Flask API for the assistant
│       └── README.md               # Documentation for the sommelier component
├── web/                            # Frontend for Sommelier Assistant
│   ├── src/                        # React source files
│   │   ├── components/             # UI components (ChatPanel, MetricsPanel, etc.)
│   │   ├── pages/                  # Application pages
│   │   └── services/               # API integration services
│   ├── package.json                # Node.js dependencies
│   └── README.md                   # Frontend documentation
├── .gitignore                      # Specifies files to ignore in Git
├── LICENSE                         # License information
├── README.md                       # This file
└── requirements.txt                # Python dependencies
```

## 🚀 Installation

1. Clone this repository:
   ```
   git clone https://github.com/PavoWillow/wine-data-toolkit.git
   cd wine-data-toolkit
   ```

2. Install Python dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up your Algolia account:
   - Create an account at [Algolia](https://www.algolia.com/)
   - Get your Application ID and API Key from the Algolia dashboard

4. For the web interface, install Node.js dependencies:
   ```
   cd web
   npm install
   ```

## 💻 Usage

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

### 4. Run the Sommelier AI Assistant

#### Backend API

```bash
cd src/sommelier
python app.py --app-id YOUR_APP_ID --api-key YOUR_API_KEY --index your_enriched_index_name
```

#### Command Line Interface

If you prefer to interact with the sommelier via CLI:

```bash
cd src/sommelier
python sommelier_ai_assistant.py --app-id YOUR_APP_ID --api-key YOUR_API_KEY --index your_enriched_index_name
```

#### Web Interface

```bash
cd web
npm run dev
```

Then open your browser to the URL shown in the terminal (typically http://localhost:5173)

## 📊 Sommelier AI Features

The Sommelier AI Assistant offers:

- **Multiple Query Types**: Specialized handling for recommendations, food pairings, wine education, vineyard information, and tasting guidance
- **Intelligent Caching**: Efficiently reuses responses for similar queries to improve performance and reduce costs
- **Metrics Dashboard**: Real-time analytics showing:
  - Cache hit/miss rate
  - Response time comparisons
  - Cost savings estimates
  - Performance by query type
- **Interactive Web Interface**: Chat with the sommelier and see analytics in a user-friendly dashboard
- **Command-line Interface**: Direct access via the terminal with metrics commands

Example queries you can try:
- "What wine would pair well with steak?"
- "Tell me about Cabernet Sauvignon grapes"
- "Recommend a good white wine under $30"
- "Explain primary, secondary, and tertiary tastes"
- "What's the soil like in Bordeaux vineyards?"

## 🔑 Required API Keys

- **Algolia**: You'll need an Application ID and API Key from your Algolia account

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📞 Contact

Feel free to reach out with questions or feedback about the Wine Data Toolkit.
