import requests
import json
import csv
import time
import os
import random
from datetime import datetime
from tqdm import tqdm  # For progress bars

def fetch_vivino_wines(query=None, page=1, per_page=50, wine_type_ids=None, country_codes=None, min_rating=None):
    """
    Fetch wine data from Vivino API with flexible parameters
    
    Args:
        query: Search term (varietal, region, etc.)
        page: Page number for pagination
        per_page: Number of results per page (max 50)
        wine_type_ids: List of wine type IDs to filter by
        country_codes: List of country codes to filter by
        min_rating: Minimum rating filter
    """
    base_url = "https://www.vivino.com/api/explore/explore"
    
    # Default parameters
    params = {
        "page": page,
        "per_page": per_page,
        "currency_code": "USD",
        "sort_by": "high_rating"
    }
    
    # Add optional filters
    if query:
        params["q"] = query
    
    if wine_type_ids:
        params["wine_type_ids[]"] = wine_type_ids
    
    if country_codes:
        params["country_codes[]"] = country_codes
    else:
        # Default to major wine producing countries
        params["country_codes[]"] = ["fr", "it", "us", "es", "ar", "cl", "au", "nz", "de", "pt", "za"]
    
    # Add filter for minimum rating
    if min_rating:
        params["min_rating"] = min_rating
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "application/json"
    }
    
    try:
        response = requests.get(base_url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None

def extract_wine_data(wine_match):
    """
    Extract relevant wine data from API response and structure it consistently
    """
    try:
        # Safely navigate the data structure
        vintage = wine_match.get("vintage", {})
        wine = vintage.get("wine", {}) if vintage else {}
        
        if not wine:
            return None
        
        # Basic wine details
        wine_id = wine.get("id")
        vintage_id = vintage.get("id") if vintage else None
        
        # Skip if we don't have a valid ID
        if not wine_id:
            return None
            
        # Create unique ID for this wine (combining wine and vintage)
        object_id = f"wine-{wine_id}-{vintage_id}" if vintage_id else f"wine-{wine_id}"
        
        # Extract wine data
        wine_data = {
            "object_id": object_id,
            "wine_id": wine_id,
            "vintage_id": vintage_id,
            "name": wine.get("name", ""),
            "seo_name": wine.get("seo_name", ""),
            "year": vintage.get("year", "NV"),
            
            # Winery info
            "winery_id": wine.get("winery", {}).get("id") if wine.get("winery") else None,
            "winery_name": wine.get("winery", {}).get("name", "") if wine.get("winery") else "",
            
            # Wine type
            "type_id": wine.get("type_id"),
            "type_name": get_wine_type_name(wine.get("type_id")),
            
            # Region and location
            "region_id": wine.get("region", {}).get("id") if wine.get("region") else None,
            "region_name": wine.get("region", {}).get("name", "") if wine.get("region") else "",
            "country_code": wine.get("region", {}).get("country", {}).get("code", "") if wine.get("region", {}).get("country") else "",
            "country_name": wine.get("region", {}).get("country", {}).get("name", "") if wine.get("region", {}).get("country") else "",
            
            # Ratings
            "average_rating": wine.get("statistics", {}).get("ratings_average") if wine.get("statistics") else None,
            "ratings_count": wine.get("statistics", {}).get("ratings_count") if wine.get("statistics") else None,
            
            # Price
            "price": vintage.get("price", {}).get("amount") if vintage and vintage.get("price") else None,
            "price_currency": vintage.get("price", {}).get("currency", {}).get("code") if vintage and vintage.get("price", {}).get("currency") else None,
            
            # Grapes/Varietals
            "grape_ids": [grape.get("id") for grape in wine.get("grapes", []) if grape.get("id")],
            "grape_names": [grape.get("name") for grape in wine.get("grapes", []) if grape.get("name")],
            
            # Taste profile when available
            "taste_structure": wine.get("taste", {}).get("structure", {}) if wine.get("taste") else {},
            "taste_flavor": wine.get("taste", {}).get("flavor", {}) if wine.get("taste") else {},
            
            # Food pairings
            "food_pairings": wine.get("food_pairings", []),
            
            # Images
            "image_url": wine.get("image", {}).get("variations", {}).get("medium") if wine.get("image", {}).get("variations") else None,
            "thumbnail_url": wine.get("image", {}).get("variations", {}).get("small_square") if wine.get("image", {}).get("variations") else None,
            
            # Wine style if available
            "style_id": wine.get("style", {}).get("id") if wine.get("style") else None,
            "style_name": wine.get("style", {}).get("name", "") if wine.get("style") else "",
            
            # Metadata
            "vivino_url": f"https://www.vivino.com/wines/{wine.get('seo_name')}/{wine_id}" if wine.get('seo_name') else None,
            "scraped_at": datetime.now().isoformat()
        }
        
        return wine_data
        
    except Exception as e:
        print(f"Error extracting wine data: {e}")
        return None

def get_wine_type_name(type_id):
    """Convert wine type ID to readable name"""
    wine_types = {
        1: "Red", 
        2: "White", 
        3: "Sparkling", 
        4: "Rosé", 
        7: "Dessert", 
        24: "Fortified"
    }
    return wine_types.get(type_id, "Unknown")

def save_to_json(wines, filename):
    """Save wines data to JSON file"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(wines, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving to JSON: {e}")
        return False

def save_to_csv(wines, filename):
    """Save wines data to CSV file"""
    if not wines:
        print("No wines to save")
        return False
    
    try:
        # Get all possible fields from the data
        all_fields = set()
        for wine in wines:
            all_fields.update(wine.keys())
        
        # Sort fields to ensure consistent column order
        fieldnames = sorted(list(all_fields))
        
        with open(filename, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for wine in wines:
                # Handle nested structures and lists for CSV format
                row = {}
                for key, value in wine.items():
                    if isinstance(value, dict):
                        row[key] = json.dumps(value)
                    elif isinstance(value, list):
                        row[key] = json.dumps(value)
                    else:
                        row[key] = value
                writer.writerow(row)
                
        return True
    except Exception as e:
        print(f"Error saving to CSV: {e}")
        return False

def scrape_vivino_comprehensive(max_wines=5000, wines_per_query=200, save_interval=500):
    """
    Scrape a comprehensive set of wines from Vivino
    
    Args:
        max_wines: Maximum total wines to collect
        wines_per_query: How many wines to try to collect per query/category
        save_interval: Save progress after this many new wines
    """
    # Create output directory
    output_dir = "vivino_wine_data"
    os.makedirs(output_dir, exist_ok=True)
    
    # Timestamp for filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Master collection of all wines
    all_wines = {}  # Use dict for deduplication by object_id
    
    # Track progress
    total_wines_collected = 0
    last_save_count = 0
    
    # Define grape varietals to search
    grape_varietals = [
        "cabernet sauvignon", 
        "cabernet franc", 
        "pinot noir", 
        "grenache",
        "merlot", 
        "syrah", 
        "shiraz",
        "zinfandel", 
        "malbec",
        "chardonnay", 
        "sauvignon blanc", 
        "riesling", 
        "pinot grigio", 
        "gewurztraminer",
        "champagne", 
        "prosecco", 
        "cava"
    ]
    
    # Specific wine types
    wine_types = [
        {"id": 1, "name": "Red"},
        {"id": 2, "name": "White"},
        {"id": 3, "name": "Sparkling"},
        {"id": 4, "name": "Rosé"},
        {"id": 7, "name": "Dessert"},
        {"id": 24, "name": "Fortified"}
    ]
    
    # Countries to search (expanding to more wine regions)
    countries = [
        {"code": "fr", "name": "France"},
        {"code": "it", "name": "Italy"},
        {"code": "us", "name": "United States"},
        {"code": "es", "name": "Spain"},
        {"code": "ar", "name": "Argentina"},
        {"code": "cl", "name": "Chile"},
        {"code": "au", "name": "Australia"},
        {"code": "nz", "name": "New Zealand"},
        {"code": "pt", "name": "Portugal"},
        {"code": "de", "name": "Germany"},
        {"code": "za", "name": "South Africa"},
        {"code": "at", "name": "Austria"},
        {"code": "gr", "name": "Greece"}
    ]
    
    # Rating tiers for diversity
    rating_tiers = [
        {"min": 4.0, "name": "Excellent"},
        {"min": 3.5, "name": "Very Good"},
        {"min": 3.0, "name": "Good"}
    ]
    
    # Build search strategies
    search_strategies = []
    
    # 1. Search by grape varietals (most specific)
    for varietal in grape_varietals:
        search_strategies.append({
            "query": varietal,
            "wine_type_ids": None,
            "country_codes": None,
            "min_rating": 3.5,  # Focus on quality wines
            "description": f"Wines of {varietal}"
        })
    
    # 2. Search by wine type across all countries
    for wine_type in wine_types:
        for rating_tier in rating_tiers:
            search_strategies.append({
                "query": None,
                "wine_type_ids": [wine_type["id"]],
                "country_codes": None,
                "min_rating": rating_tier["min"],
                "description": f"{rating_tier['name']} {wine_type['name']} wines"
            })
    
    # 3. Search by country and wine type combinations
    for country in countries:
        for wine_type in wine_types:
            search_strategies.append({
                "query": None,
                "wine_type_ids": [wine_type["id"]],
                "country_codes": [country["code"]],
                "min_rating": 3.8,  # Focus on better wines for country-specific searches
                "description": f"{wine_type['name']} wines from {country['name']}"
            })
    
    # 4. Add some premium wine searches (top-rated across all categories)
    search_strategies.append({
        "query": "premium",
        "wine_type_ids": None,
        "country_codes": None,
        "min_rating": 4.5,
        "description": "Premium wines across all types"
    })
    
    # Randomize strategies to avoid hammering specific categories
    random.shuffle(search_strategies)
    
    # Function to save progress
    def save_progress():
        nonlocal last_save_count
        
        if total_wines_collected <= last_save_count:
            return  # Nothing new to save
            
        # Convert to list for output
        wines_list = list(all_wines.values())
        
        # Checkpoint files
        checkpoint_json = os.path.join(output_dir, f"vivino_wines_{timestamp}_checkpoint_{total_wines_collected}.json")
        checkpoint_csv = os.path.join(output_dir, f"vivino_wines_{timestamp}_checkpoint_{total_wines_collected}.csv")
        
        print(f"\nSaving checkpoint with {total_wines_collected} wines...")
        save_to_json(wines_list, checkpoint_json)
        save_to_csv(wines_list, checkpoint_csv)
        
        last_save_count = total_wines_collected
    
    # Main execution loop
    try:
        print(f"Starting comprehensive Vivino wine data collection (target: {max_wines} wines)...")
        print(f"Using {len(search_strategies)} different search strategies")
        
        # Loop through each search strategy
        for strategy_index, strategy in enumerate(search_strategies):
            # Check if we've reached the overall target
            if total_wines_collected >= max_wines:
                print(f"Reached overall target of {max_wines} wines")
                break
                
            # Calculate how many more wines we need
            remaining_target = max_wines - total_wines_collected
            current_target = min(wines_per_query, remaining_target)
            
            if current_target <= 0:
                break
                
            query = strategy["query"]
            wine_type_ids = strategy["wine_type_ids"]
            country_codes = strategy["country_codes"]
            min_rating = strategy["min_rating"]
            description = strategy["description"]
            
            print(f"\nStrategy {strategy_index+1}/{len(search_strategies)}: {description}")
            print(f"Target: Collect up to {current_target} wines from this category")
            
            # Initialize for this strategy
            strategy_wines_collected = 0
            current_page = 1
            max_pages = 20  # Limit to avoid excessive pagination
            
            # Paginate through results for this strategy
            while strategy_wines_collected < current_target and current_page <= max_pages:
                print(f"  Fetching page {current_page}...")
                
                # Fetch data
                response = fetch_vivino_wines(
                    query=query,
                    page=current_page,
                    per_page=50,  # Maximum allowed by API
                    wine_type_ids=wine_type_ids,
                    country_codes=country_codes,
                    min_rating=min_rating
                )
                
                # Check for valid response
                if not response or "explore_vintage" not in response:
                    print("  No valid data found, skipping to next strategy")
                    break
                    
                # Extract matches
                matches = response.get("explore_vintage", {}).get("matches", [])
                
                if not matches:
                    print("  No matches found on this page")
                    break
                
                print(f"  Found {len(matches)} wines on page {current_page}")
                
                # Process wines from this page
                new_wines_on_page = 0
                
                for match in matches:
                    wine_data = extract_wine_data(match)
                    
                    if wine_data and wine_data["object_id"]:
                        # Check if we already have this wine
                        if wine_data["object_id"] not in all_wines:
                            all_wines[wine_data["object_id"]] = wine_data
                            strategy_wines_collected += 1
                            total_wines_collected += 1
                            new_wines_on_page += 1
                            
                            # Check if we've reached our targets
                            if strategy_wines_collected >= current_target:
                                print(f"  Reached target for this strategy: {strategy_wines_collected} wines")
                                break
                                
                            if total_wines_collected >= max_wines:
                                print(f"  Reached overall target: {total_wines_collected} wines")
                                break
                
                # Show progress
                print(f"  Added {new_wines_on_page} new wines from page {current_page}")
                print(f"  Progress: {strategy_wines_collected}/{current_target} for this strategy, {total_wines_collected}/{max_wines} overall")
                
                # Check if we need to save a checkpoint
                if total_wines_collected - last_save_count >= save_interval:
                    save_progress()
                
                # If no new wines on this page, no need to continue pagination
                if new_wines_on_page == 0:
                    print("  No new wines found on this page, moving to next strategy")
                    break
                
                # Increment page and add a delay to be nice to the API
                current_page += 1
                time.sleep(random.uniform(1.5, 3.0))  # Random delay between 1.5-3 seconds
            
            # Summary for this strategy
            print(f"Completed strategy: {description}")
            print(f"Collected {strategy_wines_collected} wines from this category")
            
            # Add a longer delay between strategies
            delay = random.uniform(3, 6)
            print(f"Waiting {delay:.1f} seconds before next strategy...")
            time.sleep(delay)
        
        # Save final results
        wines_list = list(all_wines.values())
        
        final_json = os.path.join(output_dir, f"vivino_wines_{timestamp}_final_{len(wines_list)}.json")
        final_csv = os.path.join(output_dir, f"vivino_wines_{timestamp}_final_{len(wines_list)}.csv")
        
        print(f"\nSaving final dataset with {len(wines_list)} wines...")
        save_to_json(wines_list, final_json)
        save_to_csv(wines_list, final_csv)
        
        print(f"\nData collection complete. Collected {len(wines_list)} unique wines.")
        print(f"Data saved to {output_dir} directory.")
        
        return wines_list
        
    except KeyboardInterrupt:
        print("\nCollection interrupted by user.")
        save_progress()
        return list(all_wines.values())
    
    except Exception as e:
        print(f"\nError during collection: {e}")
        save_progress()
        return list(all_wines.values())

def main():
    # Install tqdm if needed
    try:
        import tqdm
    except ImportError:
        print("Installing tqdm for progress tracking...")
        import pip
        pip.main(['install', 'tqdm'])
        import tqdm
    
    # Ask user for collection size
    try:
        target_wines = input("Enter the number of wines to collect (default: 1000, enter 'all' for comprehensive collection): ")
        
        if target_wines.lower() == 'all':
            target_wines = 10000  # A reasonable upper limit
        else:
            target_wines = int(target_wines) if target_wines.strip() else 1000
    except:
        target_wines = 1000
        print(f"Using default target of {target_wines} wines")
    
    # Execute comprehensive scraping
    scrape_vivino_comprehensive(
        max_wines=target_wines,
        wines_per_query=min(500, target_wines // 5),  # Adjust based on total target
        save_interval=min(500, target_wines // 4)     # Save at reasonable intervals
    )

if __name__ == "__main__":
    main()