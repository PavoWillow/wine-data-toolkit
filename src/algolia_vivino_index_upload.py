import os
import json
import time
import random
from algoliasearch.search_client import SearchClient
import argparse
from tqdm import tqdm

def load_json_file(filename):
    """Load wines data from JSON file"""
    try:
        print(f"Loading JSON file: {filename}")
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"Successfully loaded JSON with {len(data)} records")
            return data
    except Exception as e:
        print(f"Error loading JSON file {filename}: {e}")
        return []

def prepare_wines_for_algolia(wines):
    """
    Prepare wine data for Algolia by:
    1. Ensuring all wines have a unique objectID
    2. Creating price ranges for faceting
    3. Cleaning and formatting data
    
    Returns:
        List of wines ready for Algolia
    """
    print(f"Preparing {len(wines)} wines for Algolia...")
    prepared_wines = []
    skipped_count = 0
    
    for wine in wines:
        # Skip invalid entries
        if not wine or not isinstance(wine, dict):
            skipped_count += 1
            continue
        
        # Ensure we have a unique ID for Algolia
        if 'object_id' in wine:
            wine['objectID'] = wine['object_id']
        elif 'wine_id' in wine:
            # Create an ID if it doesn't exist
            vintage_id = wine.get('vintage_id', 'nv')
            wine['objectID'] = f"wine-{wine['wine_id']}-{vintage_id}"
        else:
            # Skip wines without proper identification
            skipped_count += 1
            continue
        
        # Create price range for faceting
        price = wine.get('price')
        if price and isinstance(price, (int, float)) and price > 0:
            if price < 10:
                wine['price_range'] = 'Under $10'
            elif price < 20:
                wine['price_range'] = '$10-$20'
            elif price < 50:
                wine['price_range'] = '$20-$50'
            elif price < 100:
                wine['price_range'] = '$50-$100'
            elif price < 200:
                wine['price_range'] = '$100-$200'
            else:
                wine['price_range'] = '$200+'
        else:
            wine['price_range'] = 'Unknown'
        
        # Ensure grape_names is a list for proper faceting
        if 'grape_names' in wine and not isinstance(wine['grape_names'], list):
            try:
                # Try to convert from string if it was stored that way
                if isinstance(wine['grape_names'], str):
                    wine['grape_names'] = json.loads(wine['grape_names'])
                else:
                    wine['grape_names'] = []
            except:
                wine['grape_names'] = []
        
        # Add a searchable full text field for advanced search
        wine['_searchable_text'] = " ".join(filter(None, [
            wine.get('name', ''),
            wine.get('winery_name', ''),
            wine.get('region_name', ''),
            wine.get('country_name', ''),
            wine.get('type_name', ''),
            wine.get('style_name', ''),
            ", ".join(wine.get('grape_names', [])) if isinstance(wine.get('grape_names', []), list) else ''
        ]))
        
        prepared_wines.append(wine)
    
    print(f"Prepared {len(prepared_wines)} wines for upload ({skipped_count} skipped)")
    return prepared_wines

def retry_with_backoff(func, max_retries=5, initial_backoff=5, max_backoff=60):
    """
    Retry a function with exponential backoff
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retry attempts
        initial_backoff: Initial backoff time in seconds
        max_backoff: Maximum backoff time in seconds
    
    Returns:
        Result of the function call
    """
    retries = 0
    backoff = initial_backoff
    
    while True:
        try:
            return func()
        except Exception as e:
            retries += 1
            if retries > max_retries:
                print(f"Maximum retries reached. Last error: {e}")
                raise
            
            # Add randomness to backoff (jitter)
            jitter = random.uniform(0, 1)
            sleep_time = min(backoff + jitter, max_backoff)
            
            print(f"Attempt {retries}/{max_retries} failed: {e}")
            print(f"Retrying in {sleep_time:.2f} seconds...")
            
            time.sleep(sleep_time)
            
            # Exponential backoff
            backoff = min(backoff * 2, max_backoff)

def clear_algolia_index(app_id, api_key, index_name):
    """
    Clear all records from an Algolia index
    
    Args:
        app_id: Algolia Application ID
        api_key: Algolia API Key
        index_name: Algolia Index Name
    
    Returns:
        True if successful, False otherwise
    """
    try:
        print(f"Connecting to Algolia with app_id: {app_id}")
        client = SearchClient.create(app_id, api_key)
        index = client.init_index(index_name)
        
        # Check if index exists and has records
        try:
            settings = index.get_settings()
            total_records = settings.get('numberOfObjects', 0)
            print(f"Found index '{index_name}' with approximately {total_records} records")
        except Exception as e:
            print(f"Error getting index info: {e}")
            print("Index may not exist yet, which is okay")
            return True
        
        # Clear all records
        print(f"Clearing all records from index '{index_name}'...")
        
        def clear_records():
            response = index.clear_objects()
            response.wait()
            return True
            
        retry_with_backoff(clear_records)
        
        print(f"Successfully cleared all records from index '{index_name}'")
        return True
        
    except Exception as e:
        print(f"Error clearing Algolia index: {e}")
        return False

def configure_algolia_index(index):
    """
    Configure index settings for optimal wine search
    
    Args:
        index: Algolia index object
    
    Returns:
        True if successful, False otherwise
    """
    try:
        print("Configuring index settings...")
        
        def update_settings():
            response = index.set_settings({
                # Set searchable attributes in order of importance
                'searchableAttributes': [
                    'name',
                    'winery_name',
                    'grape_names',
                    'region_name',
                    'country_name',
                    'type_name',
                    'style_name'
                ],
                
                # Set attributes for faceting (filtering)
                'attributesForFaceting': [
                    'type_name',
                    'country_name',
                    'region_name',
                    'searchable(grape_names)',
                    'searchable(winery_name)',
                    'year',
                    'price_range'  # We'll create this during processing
                ],
                
                # Custom ranking to sort results
                'customRanking': [
                    'desc(average_rating)',
                    'desc(ratings_count)'
                ],
                
                # Allow typos in search
                'typoTolerance': True,
                
                # Number of hits per page
                'hitsPerPage': 20
            })
            response.wait()
            return True
            
        retry_with_backoff(update_settings)
        
        print("Index configuration complete")
        return True
        
    except Exception as e:
        print(f"Error configuring index: {e}")
        return False

def upload_to_algolia(index, wines, batch_size=250):
    """
    Upload wines to Algolia in batches with retry logic
    
    Args:
        index: Algolia index object
        wines: List of wine data to upload
        batch_size: Size of batches for uploading
    
    Returns:
        Number of wines uploaded
    """
    if not wines:
        print("No wines to upload")
        return 0
    
    total_wines = len(wines)
    total_batches = (total_wines + batch_size - 1) // batch_size  # Ceiling division
    
    print(f"Uploading {total_wines} wines to Algolia in {total_batches} batches...")
    print(f"Using batch size of {batch_size} records")
    
    uploaded_count = 0
    checkpoint_file = "algolia_upload_checkpoint.json"
    
    # Check if we have a checkpoint to resume from
    if os.path.exists(checkpoint_file):
        try:
            with open(checkpoint_file, 'r') as f:
                checkpoint_data = json.load(f)
                if 'last_uploaded_index' in checkpoint_data:
                    start_index = checkpoint_data['last_uploaded_index'] + 1
                    print(f"Resuming upload from index {start_index} (completed {start_index} of {total_wines})")
                else:
                    start_index = 0
        except Exception:
            start_index = 0
    else:
        start_index = 0
    
    # Process in batches
    for i in tqdm(range(start_index, total_wines, batch_size)):
        batch = wines[i:i + batch_size]
        batch_num = i//batch_size + 1
        print(f"\nUploading batch {batch_num}/{total_batches} ({len(batch)} records)...")
        
        try:
            # Use retry logic for the upload
            def upload_batch():
                response = index.save_objects(batch)
                response.wait()
                return len(batch)
            
            batch_uploaded = retry_with_backoff(upload_batch)
            uploaded_count += batch_uploaded
            
            # Save checkpoint
            with open(checkpoint_file, 'w') as f:
                json.dump({'last_uploaded_index': i + len(batch) - 1}, f)
            
            print(f"Batch {batch_num} uploaded successfully. Progress: {i + len(batch)}/{total_wines}")
            
            # Give Algolia a moment to process between batches
            if i + batch_size < total_wines:
                sleep_time = random.uniform(2, 5)  # Random delay between 2-5 seconds
                print(f"Waiting {sleep_time:.2f} seconds before next batch...")
                time.sleep(sleep_time)
                
        except Exception as e:
            print(f"Failed to upload batch {batch_num} after multiple retries: {e}")
            print(f"Stopping at index {i}. You can resume from this point later.")
            # Save checkpoint at the last successful batch
            with open(checkpoint_file, 'w') as f:
                json.dump({'last_uploaded_index': i - 1}, f)
            break
    
    return uploaded_count

def main():
    parser = argparse.ArgumentParser(description='Clear and re-upload Vivino wine data to Algolia')
    parser.add_argument('--app-id', required=True, 
                        help='Algolia Application ID')
    parser.add_argument('--api-key', required=True, 
                        help='Algolia Admin API Key')
    parser.add_argument('--index-name', required=True, 
                        help='Algolia Index Name')
    parser.add_argument('--file', default='vivino_wine_data/vivino_wines_latest.json',
                        help='Path to the JSON file to upload')
    parser.add_argument('--batch-size', type=int, default=250, 
                        help='Batch size for uploading to Algolia (default: 250)')
    parser.add_argument('--skip-clear', action='store_true',
                        help='Skip clearing the index (only upload)')
    parser.add_argument('--resume', action='store_true',
                        help='Resume from last checkpoint (only applies if --skip-clear is used)')
    
    args = parser.parse_args()
    
    # Print settings
    print("\n===== Algolia Clean & Reindex Script =====")
    print("\nSettings:")
    print(f"  Algolia App ID:   {args.app_id}")
    print(f"  Algolia Index:    {args.index_name}")
    print(f"  Data File:        {args.file}")
    print(f"  Batch Size:       {args.batch_size}")
    print(f"  Skip Clear:       {args.skip_clear}")
    print(f"  Resume Upload:    {args.resume}")
    print("")
    
    # Check if resume flag is used with clear
    if args.resume and not args.skip_clear:
        print("Warning: --resume flag only works with --skip-clear. Will clear index and start fresh.")
        args.resume = False
    
    # Initialize Algolia client
    print("Initializing Algolia client...")
    client = SearchClient.create(args.app_id, args.api_key)
    index = client.init_index(args.index_name)
    
    # Clear the index if not skipped
    if not args.skip_clear:
        if not clear_algolia_index(args.app_id, args.api_key, args.index_name):
            print("Failed to clear index. Exiting.")
            return
        
        # Remove checkpoint file if it exists
        checkpoint_file = "algolia_upload_checkpoint.json"
        if os.path.exists(checkpoint_file):
            os.remove(checkpoint_file)
    
    # Configure the index
    if not configure_algolia_index(index):
        print("Failed to configure index. Exiting.")
        return
    
    # Load the wine data
    wines = load_json_file(args.file)
    if not wines:
        print("Failed to load wine data. Exiting.")
        return
    
    # Prepare the data for Algolia
    prepared_wines = prepare_wines_for_algolia(wines)
    if not prepared_wines:
        print("Failed to prepare wine data. Exiting.")
        return
    
    # Upload the data
    uploaded = upload_to_algolia(index, prepared_wines, args.batch_size)
    
    print(f"\nSuccessfully uploaded {uploaded} wines to Algolia index '{args.index_name}'")
    
    if uploaded > 0:
        # Remove the checkpoint file if the upload completed successfully
        checkpoint_file = "algolia_upload_checkpoint.json"
        if os.path.exists(checkpoint_file):
            os.remove(checkpoint_file)
            print("Upload checkpoint cleared.")
            
        print("Your wine data is now searchable in Algolia without duplicates!")
    else:
        print("No wines were uploaded. Check the error messages above.")

if __name__ == "__main__":
    main()