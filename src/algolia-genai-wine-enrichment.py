import os
import json
import time
import requests
import argparse
from datetime import datetime
from tqdm import tqdm
from algoliasearch.search_client import SearchClient
from concurrent.futures import ThreadPoolExecutor, as_completed

class AlgoliaClient:
    """Handles interactions with Algolia's regular Search API"""
    
    def __init__(self, app_id, api_key, source_index_name, target_index_name=None):
        """
        Initialize the Algolia client and indexes
        
        Args:
            app_id: Algolia Application ID
            api_key: Algolia API Key
            source_index_name: Index name where original wine data is stored
            target_index_name: Index name where enriched data will be stored (if None, will use source_index)
        """
        self.app_id = app_id
        self.api_key = api_key
        self.source_index_name = source_index_name
        self.target_index_name = target_index_name or source_index_name
        
        self.client = SearchClient.create(app_id, api_key)
        self.source_index = self.client.init_index(source_index_name)
        
        # Initialize target index (create if it doesn't exist)
        if target_index_name and target_index_name != source_index_name:
            self.target_index = self.client.init_index(target_index_name)
            self._setup_target_index()
        else:
            self.target_index = self.source_index
    
    def _setup_target_index(self):
        """Set up the target index with the same settings as the source index"""
        try:
            # Get settings from source index
            settings = self.source_index.get_settings()
            
            # Remove settings that might cause issues when copying
            if 'replicas' in settings:
                del settings['replicas']
                
            # Configure target index with the same settings
            self.target_index.set_settings(settings)
            print(f"Successfully configured target index {self.target_index_name}")
            
        except Exception as e:
            print(f"Warning: Could not copy settings to target index: {e}")
    
    def list_objects(self, index_name, batch_size=1000, limit=None):
        """
        List all objects from an index without using search (uses browse API)
        
        Args:
            index_name: Name of the index to list objects from
            batch_size: Batch size for pagination
            limit: Maximum number of objects to return (None for all)
            
        Returns:
            List of objects
        """
        try:
            index = self.client.init_index(index_name)
            objects = []
            
            # Use browseObjects which doesn't count as a search operation
            browser = index.browse_objects({'batch': batch_size})
            
            for hit in browser:
                objects.append(hit)
                if limit and len(objects) >= limit:
                    objects = objects[:limit]
                    break
                    
            print(f"Retrieved {len(objects)} objects from index {index_name}")
            return objects
        except Exception as e:
            print(f"Error listing objects from {index_name}: {e}")
            return []
    
    def get_all_wines(self, batch_size=1000, filters=None, limit=None):
        """
        Fetch all wine records from the source index in batches
        
        Args:
            batch_size: Number of records to fetch per batch
            filters: Filter query to apply
            limit: Maximum number of records to fetch (None for all)
            
        Returns:
            List of wine records
        """
        wines = []
        page = 0
        
        while True:
            params = {
                'hitsPerPage': batch_size,
                'page': page
            }
            
            if filters:
                params['filters'] = filters
                
            results = self.source_index.search('', params)
            current_batch = results['hits']
            
            if not current_batch:
                break
                
            wines.extend(current_batch)
            page += 1
            
            # Check if we've reached the limit
            if limit and len(wines) >= limit:
                wines = wines[:limit]
                break
                
            if len(current_batch) < batch_size:
                break
                
        print(f"Retrieved {len(wines)} wines from Algolia index {self.source_index_name}")
        return wines
    
    def get_wine_by_id(self, object_id):
        """Fetch a single wine record by object ID from the source index"""
        try:
            return self.source_index.get_object(object_id)
        except Exception as e:
            print(f"Error fetching wine with ID {object_id}: {e}")
            return None
    
    def save_enriched_wine(self, wine_data):
        """
        Save an enriched wine record to the target index
        
        Args:
            wine_data: The enriched wine data to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure objectID is present
            object_id = wine_data.get('objectID')
            if not object_id:
                raise ValueError("Wine data must include objectID")
                
            # Save to target index
            self.target_index.save_object(wine_data)
            return True
        except Exception as e:
            print(f"Error saving enriched wine with ID {wine_data.get('objectID')}: {e}")
            return False
            
    def save_enriched_wines_batch(self, wines):
        """
        Save multiple enriched wine records to the target index in a batch
        
        Args:
            wines: List of enriched wine records
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not wines:
                return True
                
            self.target_index.save_objects(wines)
            return True
        except Exception as e:
            print(f"Error saving batch of {len(wines)} enriched wines: {e}")
            return False


class AlgoliaGenAIToolkit:
    """Handles interactions with Algolia's GenAI Toolkit API"""
    
    def __init__(self, app_id, api_key, region="us"):
        """Initialize the GenAI Toolkit client"""
        self.app_id = app_id
        self.api_key = api_key
        self.base_url = f"https://generative-{region}.algolia.com"
        self.headers = {
            'Content-Type': 'application/json',
            'X-Algolia-Api-Key': api_key,
            'X-Algolia-Application-ID': app_id
        }
    
    def list_data_sources(self, batch_size=1000, limit=None):
        """List all data sources"""
        client = SearchClient.create(self.app_id, self.api_key)
        index = client.init_index("algolia_rag_data_sources")
        
        try:
            browser = index.browse_objects({'batch': batch_size})
            data_sources = []
            
            for hit in browser:
                data_sources.append(hit)
                if limit and len(data_sources) >= limit:
                    data_sources = data_sources[:limit]
                    break
            
            print(f"Retrieved {len(data_sources)} data sources")
            return data_sources
        except Exception as e:
            print(f"Error listing data sources: {e}")
            return []
    
    def list_prompts(self, batch_size=1000, limit=None):
        """List all prompts"""
        client = SearchClient.create(self.app_id, self.api_key)
        index = client.init_index("algolia_rag_prompts")
        
        try:
            browser = index.browse_objects({'batch': batch_size})
            prompts = []
            
            for hit in browser:
                prompts.append(hit)
                if limit and len(prompts) >= limit:
                    prompts = prompts[:limit]
                    break
            
            print(f"Retrieved {len(prompts)} prompts")
            return prompts
        except Exception as e:
            print(f"Error listing prompts: {e}")
            return []
    
    def list_responses(self, batch_size=1000, limit=None):
        """List all responses"""
        client = SearchClient.create(self.app_id, self.api_key)
        index = client.init_index("algolia_rag_responses")
        
        try:
            browser = index.browse_objects({'batch': batch_size})
            responses = []
            
            for hit in browser:
                responses.append(hit)
                if limit and len(responses) >= limit:
                    responses = responses[:limit]
                    break
            
            print(f"Retrieved {len(responses)} responses")
            return responses
        except Exception as e:
            print(f"Error listing responses: {e}")
            return []
    
    def list_conversations(self, batch_size=1000, limit=None):
        """List all conversations"""
        client = SearchClient.create(self.app_id, self.api_key)
        index = client.init_index("algolia_rag_conversations")
        
        try:
            browser = index.browse_objects({'batch': batch_size})
            conversations = []
            
            for hit in browser:
                conversations.append(hit)
                if limit and len(conversations) >= limit:
                    conversations = conversations[:limit]
                    break
            
            print(f"Retrieved {len(conversations)} conversations")
            return conversations
        except Exception as e:
            print(f"Error listing conversations: {e}")
            return []
        
    def create_data_source(self, name, source_index, filters=None):
        """Create a data source using an existing Algolia index"""
        endpoint = f"{self.base_url}/create/data_source"
        
        data = {
            "name": name,
            "source": source_index
        }
        
        if filters:
            data["filters"] = filters
            
        try:
            # Without a LIST endpoint, we can't check if it exists
            # Just attempt to create it and handle errors appropriately
            response = requests.post(endpoint, headers=self.headers, json=data)
            response.raise_for_status()
            print(f"Successfully created data source: {name}")
            return response.json()
        except requests.exceptions.HTTPError as e:
            # If it returns a 409 (Conflict), the resource might already exist
            if hasattr(response, 'status_code') and response.status_code == 409:
                print(f"Data source '{name}' might already exist: {e}")
                # We could try to extract the ID from the error if the API returns it
                # For now, return a placeholder with the name so the code can continue
                return {"objectID": f"unknown_id_for_{name}", "name": name}
            else:
                print(f"Error creating data source: {e}")
                if hasattr(response, 'text'):
                    print(f"Response: {response.text}")
                return None
        except Exception as e:
            print(f"Error creating data source: {e}")
            return None
    
    def create_prompt(self, name, instructions, tone="natural"):
        """Create a prompt for the GenAI Toolkit"""
        endpoint = f"{self.base_url}/create/prompt"  # Note: singular, not plural
        
        data = {
            "name": name,
            "instructions": instructions,
            "tone": tone
        }
        
        try:
            # Without a LIST endpoint, we can't check if it exists
            # Just attempt to create it and handle errors appropriately
            response = requests.post(endpoint, headers=self.headers, json=data)
            response.raise_for_status()
            print(f"Successfully created prompt: {name}")
            return response.json()
        except requests.exceptions.HTTPError as e:
            # If it returns a 409 (Conflict), the resource might already exist
            if hasattr(response, 'status_code') and response.status_code == 409:
                print(f"Prompt '{name}' might already exist: {e}")
                # Return a placeholder so the code can continue
                return {"objectID": f"unknown_id_for_{name}", "name": name}
            else:
                print(f"Error creating prompt: {e}")
                if hasattr(response, 'text'):
                    print(f"Response: {response.text}")
                return None
        except Exception as e:
            print(f"Error creating prompt: {e}")
            return None
    
    def generate_response(self, query, data_source_id, prompt_id, additional_filters=None, with_object_ids=None):
        """Generate a response using the GenAI Toolkit"""
        endpoint = f"{self.base_url}/generate/response"  # Note: singular
        
        data = {
            "query": query,
            "dataSourceID": data_source_id,
            "promptID": prompt_id,
            "save": True,
            "useCache": False,
        }
        
        if additional_filters:
            data["additionalFilters"] = additional_filters
            
        if with_object_ids:
            data["withObjectIDs"] = with_object_ids
            
        max_retries = 3
        retry_delay = 5  # seconds
        
        for attempt in range(max_retries):
            try:
                response = requests.post(endpoint, headers=self.headers, json=data)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.HTTPError as e:
                if hasattr(response, 'status_code') and response.status_code == 429:  # Rate limit exceeded
                    retry_delay = int(response.headers.get('Retry-After', retry_delay * 2))
                    print(f"Rate limit exceeded. Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    continue
                elif hasattr(response, 'status_code') and response.status_code >= 500:  # Server error
                    print(f"Server error: {e}. Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue
                else:
                    print(f"HTTP error when generating response: {e}")
                    if hasattr(response, 'text'):
                        print(f"Response content: {response.text}")
                    return None
            except requests.exceptions.RequestException as e:
                print(f"Request error when generating response: {e}")
                time.sleep(retry_delay)
                retry_delay *= 2
                continue
            except Exception as e:
                print(f"Error generating response: {e}")
                if 'response' in locals() and hasattr(response, 'text'):
                    print(f"Response content: {response.text}")
                return None
                
        print(f"Failed to generate response after {max_retries} attempts")
        return None


class WineEnricher:
    """Main class for enriching wine data"""
    
    def __init__(self, algolia_client, genai_client):
        """Initialize with Algolia and GenAI clients"""
        self.algolia_client = algolia_client
        self.genai_client = genai_client
        self.data_sources = {}
        self.prompts = {}
        self.enrichment_counter = 0
        
    def setup_data_sources(self, index_name):
        """Set up data sources for different enrichment tasks"""
        # Main data source for all wines
        all_wines_ds = self.genai_client.create_data_source(
            name="All Wines", 
            source_index=index_name
        )
        if all_wines_ds:
            self.data_sources["all_wines"] = all_wines_ds.get("objectID")
        
        # You can create more specific data sources if needed
        # For example, a data source for red wines only
        red_wines_ds = self.genai_client.create_data_source(
            name="Red Wines", 
            source_index=index_name,
            filters="type_id:1"
        )
        if red_wines_ds:
            self.data_sources["red_wines"] = red_wines_ds.get("objectID")
        
        # Data source for white wines
        white_wines_ds = self.genai_client.create_data_source(
            name="White Wines", 
            source_index=index_name,
            filters="type_id:2"
        )
        if white_wines_ds:
            self.data_sources["white_wines"] = white_wines_ds.get("objectID")
        
        return self.data_sources
        
    def setup_prompts(self):
        """Set up prompts for different enrichment tasks"""
        # Taste profile prompt
        taste_profile_prompt = self.genai_client.create_prompt(
            name="Wine Taste Profile Analysis",
            instructions="""
            Analyze the wine data and create a detailed taste profile with three categories:
            
            1. Primary Tastes: These come directly from the grape and include fruit, floral, and herb flavors.
            2. Secondary Tastes: These come from the winemaking process like fermentation.
            3. Tertiary Tastes: These develop from aging, oxidation, and oak influence.
            
            Return a JSON object with these three categories as keys, each containing an array of specific taste descriptors.
            Also include overall_profile with a short description of the complete profile.
            
            Structure the response like this:
            {
                "primary_tastes": ["descriptor1", "descriptor2", ...],
                "secondary_tastes": ["descriptor1", "descriptor2", ...],
                "tertiary_tastes": ["descriptor1", "descriptor2", ...],
                "overall_profile": "Brief concise description"
            }
            
            Consider the wine's varietal, region, vintage, and any existing taste information to make accurate assessments.
            Be specific and use wine terminology that a sommelier would use.
            """
        )
        if taste_profile_prompt:
            self.prompts["taste_profile"] = taste_profile_prompt.get("objectID")
        
        # Soil profile prompt
        soil_profile_prompt = self.genai_client.create_prompt(
            name="Wine Soil Profile Analysis",
            instructions="""
            Based on the wine's region, grape varieties, and other available data, provide detailed information about the soil profile where the grapes were likely grown.
            
            Return a JSON object with the following structure:
            {
                "soil_types": ["type1", "type2", ...],
                "mineral_content": ["mineral1", "mineral2", ...],
                "drainage": "Description of soil drainage",
                "characteristics": "Overall characteristics of the soil",
                "impact_on_wine": "How this soil likely impacts the wine's characteristics"
            }
            
            Be accurate about regional soil types and use viticultural terminology.
            """
        )
        if soil_profile_prompt:
            self.prompts["soil_profile"] = soil_profile_prompt.get("objectID")
        
        # Quality assessment prompt
        quality_assessment_prompt = self.genai_client.create_prompt(
            name="Wine Quality Assessment",
            instructions="""
            Analyze the wine's characteristics and provide an assessment of its quality based on the following attributes:
            
            1. Balance: Harmony and symmetry among components (acidity, tannins, alcohol, fruit, etc.)
            2. Intensity: Concentration of flavors and strength of aromas
            3. Clarity: Definition and precision of flavors
            4. Complexity: Range of different flavors and nuances
            5. Typicity: How well the wine represents its variety and region
            
            Return a JSON object with these attributes as keys, each with:
            - A numeric score from 1-10
            - A brief explanation for the score
            - Also include an overall_quality score and assessment
            
            Structure the response like this:
            {
                "balance": {"score": 8, "explanation": "Brief explanation"},
                "intensity": {"score": 7, "explanation": "Brief explanation"},
                "clarity": {"score": 9, "explanation": "Brief explanation"},
                "complexity": {"score": 6, "explanation": "Brief explanation"},
                "typicity": {"score": 8, "explanation": "Brief explanation"},
                "overall_quality": {"score": 7.6, "explanation": "Brief summary assessment"}
            }
            
            Base your assessment on the wine's varietal, region, vintage, ratings, and any tasting notes.
            """
        )
        if quality_assessment_prompt:
            self.prompts["quality_assessment"] = quality_assessment_prompt.get("objectID")
        
        # Sommelier description prompt
        sommelier_description_prompt = self.genai_client.create_prompt(
            name="Sommelier Wine Description",
            instructions="""
            Create a compelling, detailed description of the wine that a professional sommelier might use.
            
            Consider:
            - The wine's varietal, region, and vintage
            - The winery's history and reputation
            - Tasting notes and flavor profile
            - Ideal food pairings
            - Appropriate serving temperature and decanting recommendations
            - Aging potential
            
            Return a JSON object with the following structure:
            {
                "short_description": "A concise 1-2 sentence description",
                "full_description": "A detailed 3-5 sentence description",
                "food_pairings": ["pairing1", "pairing2", "pairing3"],
                "serving_recommendations": "Temperature and decanting advice",
                "aging_potential": "Assessment of aging potential"
            }
            
            Make the descriptions engaging and informative while being factually accurate.
            """
        )
        if sommelier_description_prompt:
            self.prompts["sommelier_description"] = sommelier_description_prompt.get("objectID")
        
        # Weather profile prompt
        weather_profile_prompt = self.genai_client.create_prompt(
            name="Wine Weather Profile",
            instructions="""
            Based on the wine's region and vintage year, provide information about the typical and specific weather conditions that influenced this wine.
            
            Return a JSON object with the following structure:
            {
                "climate_type": "Overall climate classification (e.g., Mediterranean, Continental)",
                "growing_season": "Description of typical growing season in this region",
                "vintage_conditions": "Any known information about the specific vintage year",
                "temperature_patterns": "Typical temperature patterns in this region",
                "rainfall": "Typical rainfall patterns in this region",
                "weather_influence": "How these weather factors likely influenced the wine"
            }
            
            Be specific about regional climate patterns and, if possible, any known information about the vintage year.
            """
        )
        if weather_profile_prompt:
            self.prompts["weather_profile"] = weather_profile_prompt.get("objectID")
            
        # Cultural & Historical Context prompt
        cultural_history_prompt = self.genai_client.create_prompt(
            name="Wine Cultural & Historical Context",
            instructions="""
            Provide cultural and historical context about this wine's winery, region, and production methods.
            
            Return a JSON object with the following structure:
            {
                "winery_history": "Brief history of the winery if available",
                "regional_traditions": "Wine traditions of this specific region",
                "winemaking_heritage": "Heritage of the grape varieties and production methods",
                "historical_significance": "Any historical significance of this wine style or region",
                "cultural_context": "How this wine fits into the cultural context of its region"
            }
            
            Focus on factual information while making it engaging and educational.
            """
        )
        if cultural_history_prompt:
            self.prompts["cultural_history"] = cultural_history_prompt.get("objectID")
            
        # Value Assessment prompt
        value_assessment_prompt = self.genai_client.create_prompt(
            name="Wine Value Assessment",
            instructions="""
            Analyze the wine's price in relation to its quality, region, and comparable wines.
            
            Return a JSON object with the following structure:
            {
                "price_tier": "Budget/Mid-range/Premium/Luxury",
                "value_rating": A number from 1-10 where 10 is exceptional value,
                "relative_value": "How the value compares to similar wines",
                "price_justification": "Factors that justify the price point",
                "value_verdict": "Overall assessment of the wine's value proposition"
            }
            
            Consider the wine's price, quality ratings, region, grape varieties, and vintage.
            """
        )
        if value_assessment_prompt:
            self.prompts["value_assessment"] = value_assessment_prompt.get("objectID")
            
        # Ideal Serving Conditions prompt
        serving_conditions_prompt = self.genai_client.create_prompt(
            name="Wine Serving Conditions",
            instructions="""
            Provide detailed recommendations for the ideal serving conditions of this wine.
            
            Return a JSON object with the following structure:
            {
                "serving_temperature": "Specific temperature range in Celsius and Fahrenheit",
                "decanting_time": "Recommended decanting time if applicable",
                "glass_type": "Ideal glass shape and style",
                "aeration_needs": "Whether and how the wine benefits from aeration",
                "optimal_drinking_window": "When the wine is best consumed (now, specific years, etc.)",
                "storage_recommendations": "How to properly store this wine"
            }
            
            Consider the wine's type, body, age, tannin levels, and other characteristics.
            """
        )
        if serving_conditions_prompt:
            self.prompts["serving_conditions"] = serving_conditions_prompt.get("objectID")
        
        return self.prompts
    
    def enrich_wine(self, wine, enrichment_types=None):
        """
        Enrich a single wine with multiple types of information
        
        Args:
            wine: The wine record to enrich
            enrichment_types: List of enrichment types to perform, or None for all
        
        Returns:
            Dictionary with the enriched data
        """
        if enrichment_types is None:
            enrichment_types = [
                "taste_profile", 
                "soil_profile", 
                "quality_assessment", 
                "sommelier_description", 
                "weather_profile",
                "cultural_history",
                "value_assessment",
                "serving_conditions"
            ]
        
        wine_id = wine.get("objectID") or wine.get("object_id")
        
        # Create a copy of the original wine data as the base for enrichment
        enriched_data = wine.copy()
        
        # Ensure objectID is present and consistent
        enriched_data["objectID"] = wine_id
        
        # Track which enrichment types were successful
        successful_enrichments = []
        
        # Build a rich query prompt with essential wine information
        base_query = self._build_wine_query(wine)
        
        # Execute each enrichment type
        for enrichment_type in enrichment_types:
            if enrichment_type not in self.prompts:
                print(f"Warning: Prompt for {enrichment_type} not found")
                continue
                
            # Select the appropriate data source based on wine type
            data_source_id = self._select_data_source(wine)
            if not data_source_id:
                print(f"Warning: No suitable data source found for wine {wine_id}")
                continue
                
            # Generate the response
            print(f"Generating {enrichment_type} for wine {wine_id}")
            response = self.genai_client.generate_response(
                query=base_query,
                data_source_id=data_source_id,
                prompt_id=self.prompts[enrichment_type],
                with_object_ids=[wine_id]
            )
            
            if not response:
                print(f"Failed to generate {enrichment_type} for wine {wine_id}")
                continue
                
            # Parse the response and extract the JSON data
            try:
                # Look for JSON in the response
                response_text = response.get("response", "")
                json_data = self._extract_json_from_text(response_text)
                
                if json_data:
                    # Store the enrichment data under its own key
                    enriched_data[f"ai_{enrichment_type}"] = json_data
                    
                    # Also create searchable/filterable fields for specific enrichment types
                    if enrichment_type == "taste_profile" and isinstance(json_data, dict):
                        # Flatten taste descriptors for filtering
                        all_tastes = []
                        
                        # Process primary tastes
                        if "primary_tastes" in json_data and isinstance(json_data["primary_tastes"], list):
                            primary_tastes = json_data["primary_tastes"]
                            enriched_data["ai_primary_tastes"] = primary_tastes
                            all_tastes.extend(primary_tastes)
                            
                        # Process secondary tastes
                        if "secondary_tastes" in json_data and isinstance(json_data["secondary_tastes"], list):
                            secondary_tastes = json_data["secondary_tastes"]
                            enriched_data["ai_secondary_tastes"] = secondary_tastes
                            all_tastes.extend(secondary_tastes)
                            
                        # Process tertiary tastes
                        if "tertiary_tastes" in json_data and isinstance(json_data["tertiary_tastes"], list):
                            tertiary_tastes = json_data["tertiary_tastes"]
                            enriched_data["ai_tertiary_tastes"] = tertiary_tastes
                            all_tastes.extend(tertiary_tastes)
                            
                        # Combined taste profile for broader searches
                        if all_tastes:
                            enriched_data["ai_all_tastes"] = all_tastes
                    
                    # Extract soil types for filtering
                    elif enrichment_type == "soil_profile" and isinstance(json_data, dict):
                        if "soil_types" in json_data and isinstance(json_data["soil_types"], list):
                            enriched_data["ai_soil_types"] = json_data["soil_types"]
                    
                    # Extract overall quality score for filtering/sorting
                    elif enrichment_type == "quality_assessment" and isinstance(json_data, dict):
                        if "overall_quality" in json_data and isinstance(json_data["overall_quality"], dict):
                            if "score" in json_data["overall_quality"]:
                                enriched_data["ai_quality_score"] = json_data["overall_quality"]["score"]
                    
                    # Extract food pairings for filtering
                    elif enrichment_type == "sommelier_description" and isinstance(json_data, dict):
                        if "food_pairings" in json_data and isinstance(json_data["food_pairings"], list):
                            enriched_data["ai_food_pairings"] = json_data["food_pairings"]
                            
                    # Extract climate type for filtering
                    elif enrichment_type == "weather_profile" and isinstance(json_data, dict):
                        if "climate_type" in json_data and json_data["climate_type"]:
                            enriched_data["ai_climate_type"] = json_data["climate_type"]
                    
                    # Extract value rating for filtering/sorting
                    elif enrichment_type == "value_assessment" and isinstance(json_data, dict):
                        if "value_rating" in json_data:
                            enriched_data["ai_value_rating"] = json_data["value_rating"]
                        if "price_tier" in json_data:
                            enriched_data["ai_price_tier"] = json_data["price_tier"]
                            
                    successful_enrichments.append(enrichment_type)
                else:
                    print(f"No valid JSON found in response for {enrichment_type}")
                    # Store the raw response as fallback
                    enriched_data[f"ai_{enrichment_type}_raw"] = response_text
            except Exception as e:
                print(f"Error parsing response for {enrichment_type}: {e}")
                enriched_data[f"ai_{enrichment_type}_raw"] = response.get("response", "")
            
            # Respect rate limits
            time.sleep(1)
        
        # Add metadata about the enrichment process
        enriched_data["ai_enriched"] = True
        enriched_data["ai_enrichment_types"] = successful_enrichments
        
        return enriched_data
    
    def _build_wine_query(self, wine):
        """Build a comprehensive query about the wine for the GenAI model"""
        # Extract key information for the query
        wine_name = wine.get("name", "")
        winery = wine.get("winery_name", "")
        year = wine.get("year", "")
        region = wine.get("region_name", "")
        country = wine.get("country_name", "")
        grapes = wine.get("grape_names", [])
        wine_type = wine.get("type_name", "")
        avg_rating = wine.get("average_rating")
        
        if isinstance(grapes, str):
            try:
                # Try to parse grapes if they're stored as a JSON string
                grapes = json.loads(grapes)
            except:
                grapes = [grapes]
        
        # Build the query
        query = f"""
        Analyze this wine in detail:
        Name: {wine_name}
        Winery: {winery}
        Vintage Year: {year}
        Region: {region}
        Country: {country}
        Grape Varieties: {', '.join(grapes) if isinstance(grapes, list) else grapes}
        Wine Type: {wine_type}
        Average Rating: {avg_rating}
        """
        
        # Add taste structure if available
        taste_structure = wine.get("taste_structure")
        if taste_structure and isinstance(taste_structure, dict):
            if isinstance(taste_structure, str):
                try:
                    taste_structure = json.loads(taste_structure)
                except:
                    taste_structure = {}
                    
            query += "\nTaste Structure:\n"
            for key, value in taste_structure.items():
                query += f"- {key}: {value}\n"
        
        # Add taste flavor if available
        taste_flavor = wine.get("taste_flavor")
        if taste_flavor and isinstance(taste_flavor, dict):
            if isinstance(taste_flavor, str):
                try:
                    taste_flavor = json.loads(taste_flavor)
                except:
                    taste_flavor = {}
                    
            query += "\nTaste Flavor:\n"
            for key, value in taste_flavor.items():
                query += f"- {key}: {value}\n"
                
        return query
    
    def _select_data_source(self, wine):
        """Select the appropriate data source based on wine type"""
        wine_type_id = wine.get("type_id")
        
        if wine_type_id == 1:  # Red wine
            return self.data_sources.get("red_wines")
        elif wine_type_id == 2:  # White wine
            return self.data_sources.get("white_wines")
        else:
            # Default to all wines data source
            return self.data_sources.get("all_wines")
    
    def _extract_json_from_text(self, text):
        """Extract JSON object from text response"""
        try:
            # First try to parse the entire text as JSON
            return json.loads(text)
        except:
            # Look for JSON within the text
            try:
                # Look for text between curly braces
                start_idx = text.find('{')
                end_idx = text.rfind('}') + 1
                
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = text[start_idx:end_idx]
                    return json.loads(json_str)
            except:
                return None
                
    def batch_enrich_wines(self, wines, batch_size=10, max_workers=5, enrichment_types=None):
        """
        Enrich a batch of wines in parallel
        
        Args:
            wines: List of wine records to enrich
            batch_size: Number of wines to process in each batch
            max_workers: Maximum number of parallel workers
            enrichment_types: List of enrichment types to perform, or None for all
            
        Returns:
            List of enriched wine records
        """
        if enrichment_types is None:
            enrichment_types = [
                "taste_profile", 
                "soil_profile", 
                "quality_assessment", 
                "sommelier_description", 
                "weather_profile",
                "cultural_history",
                "value_assessment",
                "serving_conditions"
            ]
            
        total_enriched = 0
        enriched_batch = []
        
        # Process in batches to avoid overwhelming the API
        for i in range(0, len(wines), batch_size):
            batch = wines[i:i+batch_size]
            print(f"\nProcessing batch {i//batch_size + 1}/{(len(wines) + batch_size - 1)//batch_size}")
            
            # Process batch in parallel
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_wine = {
                    executor.submit(self.enrich_wine, wine, enrichment_types): wine 
                    for wine in batch
                }
                
                for future in tqdm(as_completed(future_to_wine), total=len(batch), desc="Enriching wines"):
                    wine = future_to_wine[future]
                    try:
                        enriched_data = future.result()
                        if enriched_data:
                            # Add enrichment timestamp
                            enriched_data['enriched_at'] = datetime.now().isoformat()
                            enriched_batch.append(enriched_data)
                            self.enrichment_counter += 1
                    except Exception as e:
                        print(f"Error enriching wine {wine.get('objectID', wine.get('object_id'))}: {e}")
            
            # Save the batch to Algolia
            if enriched_batch:
                print(f"Saving {len(enriched_batch)} enriched wines to Algolia")
                success = self.algolia_client.save_enriched_wines_batch(enriched_batch)
                if success:
                    total_enriched += len(enriched_batch)
                    print(f"Successfully saved batch. Total wines enriched so far: {total_enriched}")
                else:
                    print(f"Failed to save batch of {len(enriched_batch)} wines")
                    
                enriched_batch = []  # Reset for next batch
                
            # Pause between batches to respect rate limits
            if i + batch_size < len(wines):
                pause_time = 5
                print(f"Pausing for {pause_time} seconds between batches...")
                time.sleep(pause_time)
                
        print(f"\nEnrichment complete! Total wines enriched: {total_enriched}")
        return total_enriched


def display_results(title, items, format_type='table'):
    """Display results in a readable format"""
    if not items:
        print(f"No {title.lower()} found.")
        return
        
    print(f"\n=== {title} ({len(items)}) ===")
    
    if format_type == 'json':
        print(json.dumps(items, indent=2))
        return
    
    # Table format - determine common fields to display
    common_fields = set()
    for item in items[:5]:  # Sample first 5 items to determine fields
        common_fields.update(item.keys())
    
    # Prioritize important fields
    priority_fields = ['objectID', 'name', 'source', 'filters', 'tone', 'query', 'createdAt']
    display_fields = [f for f in priority_fields if f in common_fields]
    
    # Add a few more fields if available
    remaining_fields = sorted(list(common_fields - set(display_fields)))
    display_fields.extend(remaining_fields[:3])  # Add up to 3 more fields
    
    # Print header
    header = " | ".join(display_fields)
    print("-" * len(header))
    print(header)
    print("-" * len(header))
    
    # Print items
    for item in items:
        row = []
        for field in display_fields:
            value = item.get(field, "")
            if isinstance(value, dict) or isinstance(value, list):
                value = str(type(value).__name__)  # Just show type for complex objects
            elif isinstance(value, str) and len(value) > 30:
                value = value[:27] + "..."  # Truncate long strings
            row.append(str(value))
        print(" | ".join(row))
    
    print("-" * len(header))


def main():
    """Main function to run the wine enrichment process"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Enrich wine data with Algolia GenAI Toolkit')
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Enrich wine data with Algolia GenAI Toolkit')
    
    parser.add_argument('--app-id', required=True,
                        help='Algolia Application ID')
    parser.add_argument('--api-key', required=True,
                        help='Algolia API Key')
    parser.add_argument('--source-index', required=True,
                        help='Source Algolia index name containing wine data')
    parser.add_argument('--target-index', default=None,
                        help='Target Algolia index name for storing enriched data (default: same as source)')
    parser.add_argument('--genai-region', default="us", choices=['us', 'eu'],
                        help='Algolia GenAI Toolkit region (default: us)')

    
    # Add new arguments for listing operations
    list_group = parser.add_argument_group('Listing operations')
    list_group.add_argument('--list-data-sources', action='store_true',
                         help='List all data sources')
    list_group.add_argument('--list-prompts', action='store_true',
                         help='List all prompts')
    list_group.add_argument('--list-responses', action='store_true',
                         help='List all responses')
    list_group.add_argument('--list-conversations', action='store_true',
                         help='List all conversations')
    list_group.add_argument('--output-format', choices=['json', 'table'], default='table',
                         help='Output format for listing operations (default: table)')
    list_group.add_argument('--output-file', 
                         help='Save listing output to a file')
    
    args = parser.parse_args()
    
    # Display configuration
    print("\n=== Algolia GenAI Wine Enrichment ===")
    print(f"Source Index: {args.source_index}")
    print(f"Target Index: {args.target_index}")
    print(f"GenAI Region: {args.genai_region}")
    print(f"Batch Size: {args.batch_size}")
    print(f"Max Workers: {args.max_workers}")
    print(f"Limit: {args.limit if args.limit > 0 else 'All wines'}")
    print(f"Filter: {args.filter if args.filter else 'None'}")
    print(f"Enrichment Types: {', '.join(args.enrichment_types)}")
    print("=====================================\n")
    
    # Initialize clients
    algolia_client = AlgoliaClient(
        app_id=args.app_id,
        api_key=args.api_key,
        source_index_name=args.source_index,
        target_index_name=args.target_index
    )
    
    genai_client = AlgoliaGenAIToolkit(
        app_id=args.app_id,
        api_key=args.api_key,
        region=args.genai_region
    )
    
    # Handle listing operations
    if args.list_data_sources or args.list_prompts or args.list_responses or args.list_conversations:
        results = {}
        
        if args.list_data_sources:
            data_sources = genai_client.list_data_sources()
            results['data_sources'] = data_sources
            display_results('Data Sources', data_sources, args.output_format)
            
        if args.list_prompts:
            prompts = genai_client.list_prompts()
            results['prompts'] = prompts
            display_results('Prompts', prompts, args.output_format)
            
        if args.list_responses:
            responses = genai_client.list_responses()
            results['responses'] = responses
            display_results('Responses', responses, args.output_format)
            
        if args.list_conversations:
            conversations = genai_client.list_conversations()
            results['conversations'] = conversations
            display_results('Conversations', conversations, args.output_format)
        
        # Save results to file if requested
        if args.output_file and results:
            with open(args.output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2)
            print(f"Results saved to {args.output_file}")
        
        return
    
    # Initialize wine enricher
    enricher = WineEnricher(algolia_client, genai_client)
    
    # Setup data sources and prompts
    print("Setting up data sources...")
    data_sources = enricher.setup_data_sources(args.source_index)
    if not data_sources:
        print("Error: Failed to create data sources")
        return
        
    print("Setting up prompts...")
    prompts = enricher.setup_prompts()
    if not prompts:
        print("Error: Failed to create prompts")
        return
    
    # Get wines to enrich
    print(f"Fetching wines from Algolia index {args.source_index}...")
    wines = algolia_client.get_all_wines(filters=args.filter, limit=args.limit)
    
    if not wines:
        print("No wines found to enrich. Please check your filter criteria.")
        return
    
    print(f"Found {len(wines)} wines to enrich")
    
    # Ask for confirmation before proceeding
    confirm = input(f"Ready to enrich {len(wines)} wines. Proceed? (y/n): ")
    if confirm.lower() not in ['y', 'yes']:
        print("Enrichment cancelled.")
        return
    
    # Start the enrichment process
    start_time = time.time()
    print(f"Starting batch enrichment at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    total_enriched = enricher.batch_enrich_wines(
        wines, 
        batch_size=args.batch_size, 
        max_workers=args.max_workers,
        enrichment_types=args.enrichment_types
    )
    
    # Print summary
    elapsed_time = time.time() - start_time
    hours, remainder = divmod(elapsed_time, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    print("\n=== Enrichment Summary ===")
    print(f"Total wines processed: {len(wines)}")
    print(f"Total wines successfully enriched: {total_enriched}")
    print(f"Elapsed time: {int(hours)}h {int(minutes)}m {int(seconds)}s")
    print(f"Average time per wine: {elapsed_time/total_enriched:.2f}s" if total_enriched > 0 else "N/A")
    print(f"Enriched data stored in: {args.target_index}")
    print("=========================")


if __name__ == "__main__":
    main()