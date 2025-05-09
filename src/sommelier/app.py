# Updated app.py to use integrated SommelierAssistant with metrics

from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the integrated Sommelier Assistant
from sommelier_ai_assistant import SommelierAssistant

app = Flask(__name__)
# Configure CORS to allow requests from your React app
CORS(app, resources={r"/*": {"origins": "*"}})

# Get credentials
ALGOLIA_APP_ID = os.environ.get('ALGOLIA_APP_ID')
ALGOLIA_API_KEY = os.environ.get('ALGOLIA_API_KEY')
ALGOLIA_INDEX = os.environ.get('ALGOLIA_INDEX')
ALGOLIA_REGION = os.environ.get('ALGOLIA_REGION', 'us')
METRICS_FILE = os.environ.get('METRICS_FILE', 'sommelier_metrics.json')

# Initialize the Sommelier Assistant with integrated metrics
sommelier = SommelierAssistant(
    app_id=ALGOLIA_APP_ID,
    api_key=ALGOLIA_API_KEY,
    index_name=ALGOLIA_INDEX,
    region=ALGOLIA_REGION,
    debug=True,
    metrics_file=METRICS_FILE
)

# Test route to verify the API is working
@app.route('/test', methods=['GET'])
def test():
    return jsonify({"message": "Flask API is working!"})

# Routes for the Sommelier API
@app.route('/api/query', methods=['POST'])
def process_query():
    # Get data from request
    data = request.json
    print(f"Received query: {data}")  # Debug print
    
    query = data.get('query', '')
    prompt_type = data.get('promptType')
    
    if not query:
        return jsonify({"error": "Query is required"}), 400
    
    # Process the query (metrics tracking is now built in)
    response = sommelier.process_query(query, prompt_type)
    
    # Get prompt and data source IDs for checking cache hits 
    # (Used just to check if this was a cache hit, metrics tracking is already done)
    prompt_id = sommelier._select_prompt(query, prompt_type)
    data_source_id = sommelier._select_data_source(query)
    query_essence = sommelier._get_query_essence(query)
    object_id = sommelier._generate_stable_id(query_essence, data_source_id, prompt_id)
    
    # Check if this was a cache hit
    is_cache_hit = any(
        log_entry.get("object_id") == object_id and log_entry.get("cache_hit") 
        for log_entry in sommelier.current_session.get("query_log", [])[-10:]
    )
    
    # Get the response time from the most recent log entry
    response_time = 0
    if sommelier.current_session.get("query_log"):
        latest_entry = sommelier.current_session["query_log"][-1]
        if latest_entry.get("object_id") == object_id:
            response_time = latest_entry.get("response_time", 0)
    
    print(f"Sending response: cache_hit={is_cache_hit}, response_time={response_time}")
    
    # Return the response along with cache info
    return jsonify({
        "response": response,
        "cache_hit": is_cache_hit,
        "response_time": response_time,
        "query_type": prompt_type or "auto"
    })

@app.route('/api/metrics', methods=['GET'])
def get_metrics():
    # Calculate derived metrics before returning
    sommelier.calculate_derived_metrics()
    
    # Get the current session metrics
    session = sommelier.current_session
    
    # Format query type performance
    query_type_performance = []
    for qtype, stats in session.get("query_types", {}).items():
        hit_rate = round(stats["hits"] / stats["total"] * 100, 2) if stats["total"] > 0 else 0
        query_type_performance.append({
            "type": qtype,
            "total": stats["total"],
            "hits": stats["hits"],
            "misses": stats["misses"],
            "hit_rate": hit_rate
        })
    
    # Sort by hit rate
    query_type_performance.sort(key=lambda x: x["hit_rate"], reverse=True)
    
    # Return processed metrics
    return jsonify({
        "start_time": session["start_time"],
        "total_queries": session["total_queries"],
        "cache_hits": session["cache_hits"],
        "cache_misses": session["cache_misses"],
        "hit_rate": session.get("cache_hit_rate", 0),
        "miss_rate": session.get("cache_miss_rate", 0),
        "avg_response_time": session.get("avg_response_time", 0),
        "avg_cache_hit_time": session.get("avg_cache_hit_time", 0),
        "avg_generation_time": session.get("avg_generation_time", 0),
        "estimated_tokens_saved": session.get("estimated_tokens_saved", 0),
        "estimated_cost_saved": session.get("estimated_cost_saved", 0),
        "potential_cost_without_caching": session.get("potential_cost_without_caching", 0),
        "actual_cost_with_caching": session.get("actual_cost_with_caching", 0),
        "cost_reduction_percentage": session.get("cost_reduction_percentage", 0),
        "query_type_performance": query_type_performance,
        "recent_queries": session.get("query_log", [])[-10:] if session.get("query_log") else []
    })

@app.route('/api/prompt-types', methods=['GET'])
def get_prompt_types():
    # Return available prompt types from the sommelier assistant
    prompt_types = list(sommelier.prompts.keys())
    return jsonify({"prompt_types": prompt_types})

@app.route('/api/reset-metrics', methods=['POST'])
def reset_metrics():
    # Reset the metrics
    sommelier.reset_metrics()
    return jsonify({"message": "Metrics reset successfully"})

@app.route('/api/clear-conversation', methods=['POST'])
def clear_conversation():
    response = sommelier.clear_conversation()
    return jsonify({"message": response})

if __name__ == '__main__':
    # Check if credentials are available
    if not all([ALGOLIA_APP_ID, ALGOLIA_API_KEY, ALGOLIA_INDEX]):
        print("Error: Algolia credentials not set. Please set environment variables.")
        print("Required: ALGOLIA_APP_ID, ALGOLIA_API_KEY, ALGOLIA_INDEX")
        exit(1)
        
    print(f"Starting Sommelier API with index: {ALGOLIA_INDEX}")
    # Make sure Flask runs on 0.0.0.0 so it's accessible from other processes
    app.run(debug=True, host='0.0.0.0', port=5001)