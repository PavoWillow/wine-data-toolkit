import os
import json
import time
import cmd
import textwrap
import requests
import argparse
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import numpy as np
from colorama import Fore, Style, init
from algoliasearch.search_client import SearchClient

# Initialize colorama for colored terminal output
init()

class SommelierAssistant:
    """Main class for the Sommelier AI Assistant with integrated metrics tracking"""
    
    def __init__(self, app_id, api_key, index_name, region="us", debug=False, metrics_file="sommelier_metrics.json"):
        """Initialize the Sommelier Assistant with metrics tracking"""
        # Core assistant initialization
        self.app_id = app_id
        self.api_key = api_key
        self.index_name = index_name
        self.region = region
        self.debug = debug
        self.base_url = f"https://generative-{region}.algolia.com"
        self.headers = {
            'Content-Type': 'application/json',
            'X-Algolia-Api-Key': api_key,
            'X-Algolia-Application-ID': app_id
        }
        
        # Initialize Algolia client
        self.client = SearchClient.create(app_id, api_key)
        self.index = self.client.init_index(index_name)
        
        # Data sources and prompts
        self.data_sources = {}
        self.prompts = {}
        
        # Store prompt instructions for the semantic matcher
        self.prompt_instructions = {}
        
        # Conversation history
        self.conversation_history = []
        self.conversation_id = None
        
        # Initialize metrics tracking
        self.metrics_file = metrics_file
        self.current_session = {
            "start_time": datetime.now().isoformat(),
            "total_queries": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "api_errors": 0,
            "response_times": [],
            "cache_hit_times": [],
            "generation_times": [],
            "query_types": {},
            "query_log": [],
            "algolia_operations": {
                "search_operations": 0,
                "get_operations": 0, 
                "browse_operations": 0,
                "save_operations": 0,
                "update_operations": 0,
                "delete_operations": 0,
                "total_operations": 0,
                "operations_cost": 0.0  # If you want to track estimated API costs
            }
        }
        
        # Estimated cost per 1K tokens for LLM generation (adjust as needed)
        self.estimated_cost_per_1k_tokens = 0.002
        # Estimated tokens per response (adjust based on your average)
        self.estimated_tokens_per_response = 1000
        
        # Load previous metrics if file exists
        self.all_sessions = []
        self.load_metrics()
        
        # Initialize the semantic prompt matcher (set to None initially)
        self.semantic_matcher = None
        
        # Set up data sources and prompts
        self._setup()
        
        # Initialize semantic matcher after prompts are set up
        try:
            from semantic_prompt_matcher import SemanticPromptMatcher
            self.semantic_matcher = SemanticPromptMatcher(self.client)
            print(f"{Fore.GREEN}Semantic prompt matcher initialized{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.YELLOW}Semantic prompt matcher not available: {e}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Falling back to keyword-based prompt selection{Style.RESET_ALL}")
            self.semantic_matcher = None
    
    

    # Metrics methods
    def load_metrics(self):
        """Load metrics from file if it exists"""
        if os.path.exists(self.metrics_file):
            try:
                with open(self.metrics_file, 'r') as f:
                    data = json.load(f)
                    self.all_sessions = data.get("sessions", [])
                    print(f"{Fore.GREEN}Loaded metrics from {self.metrics_file}{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.YELLOW}Error loading metrics: {e}. Starting fresh.{Style.RESET_ALL}")
    
    def save_metrics(self):
        """Save current metrics to file"""
        # Update end time
        self.current_session["end_time"] = datetime.now().isoformat()
        
        # Calculate derived metrics
        self.calculate_derived_metrics()
        
        # Combine with previous sessions
        data = {
            "sessions": self.all_sessions + [self.current_session],
            "last_updated": datetime.now().isoformat()
        }
        
        try:
            with open(self.metrics_file, 'w') as f:
                json.dump(data, f, indent=2)
                print(f"{Fore.GREEN}Metrics saved to {self.metrics_file}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Error saving metrics: {e}{Style.RESET_ALL}")
    
    def calculate_derived_metrics(self):
        """Calculate derived metrics from raw data"""
        total = self.current_session["total_queries"]
        hits = self.current_session["cache_hits"]
        misses = self.current_session["cache_misses"]
        
        # Avoid division by zero
        if total > 0:
            self.current_session["cache_hit_rate"] = round(hits / total * 100, 2)
            self.current_session["cache_miss_rate"] = round(misses / total * 100, 2)
        else:
            self.current_session["cache_hit_rate"] = 0
            self.current_session["cache_miss_rate"] = 0
        
        # Response time averages
        if self.current_session["response_times"]:
            self.current_session["avg_response_time"] = round(
                sum(self.current_session["response_times"]) / len(self.current_session["response_times"]), 2
            )
        else:
            self.current_session["avg_response_time"] = 0
        
        if self.current_session["cache_hit_times"]:
            self.current_session["avg_cache_hit_time"] = round(
                sum(self.current_session["cache_hit_times"]) / len(self.current_session["cache_hit_times"]), 2
            )
        else:
            self.current_session["avg_cache_hit_time"] = 0
        
        if self.current_session["generation_times"]:
            self.current_session["avg_generation_time"] = round(
                sum(self.current_session["generation_times"]) / len(self.current_session["generation_times"]), 2
            )
        else:
            self.current_session["avg_generation_time"] = 0
        
        # Cost metrics
        tokens_saved = hits * self.estimated_tokens_per_response
        cost_saved = (tokens_saved / 1000) * self.estimated_cost_per_1k_tokens
        
        self.current_session["estimated_tokens_saved"] = tokens_saved
        self.current_session["estimated_cost_saved"] = round(cost_saved, 4)
        
        # If we continued without caching
        potential_cost = (total * self.estimated_tokens_per_response / 1000) * self.estimated_cost_per_1k_tokens
        actual_cost = (misses * self.estimated_tokens_per_response / 1000) * self.estimated_cost_per_1k_tokens
        
        self.current_session["potential_cost_without_caching"] = round(potential_cost, 4)
        self.current_session["actual_cost_with_caching"] = round(actual_cost, 4)
        self.current_session["cost_reduction_percentage"] = round((cost_saved / potential_cost * 100) if potential_cost > 0 else 0, 2)
    
    def _select_prompt(self, query, prompt_type=None):
        """Select the appropriate prompt based on query content or specified type"""
        # If a specific prompt type is requested, use it if available
        if prompt_type and prompt_type in self.prompts:
            # Store this prompt type as the last used one
            self.last_used_prompt_type = prompt_type
            return self.prompts[prompt_type]
        
        # For follow-up questions, use context from conversation
        query_lower = query.lower()
        follow_up_indicators = [
            "option", "sounds good", "that wine", "that one", 
            "this one", "i'll try", "i'll go with", "tell me more about"
        ]
        
        is_follow_up = any(indicator in query_lower for indicator in follow_up_indicators)
        
        # If this appears to be a follow-up question and we have conversation history
        if is_follow_up and hasattr(self, 'conversation_history') and self.conversation_history:
            # First, check if we have a stored last prompt type from previous queries
            if hasattr(self, 'last_used_prompt_type') and self.last_used_prompt_type in self.prompts:
                print(f"{Fore.CYAN}Using previous prompt type for follow-up: {self.last_used_prompt_type}{Style.RESET_ALL}")
                return self.prompts[self.last_used_prompt_type]
                
            # If we don't have a stored type, try to infer from conversation content
            if len(self.conversation_history) >= 2:
                # Look at the last assistant response for clues
                for msg in reversed(self.conversation_history):
                    if msg["role"] == "assistant":
                        last_response = msg["content"].lower()
                        
                        # Check for indicators of wine recommendations
                        if any(term in last_response for term in ["recommend", "suggestion", "option"]):
                            if "recommendations" in self.prompts:
                                self.last_used_prompt_type = "recommendations"
                                return self.prompts["recommendations"]
                        
                        # Check for food pairing context
                        if any(term in last_response for term in ["pair", "pairing", "food", "dish", "meal"]):
                            if "food_pairing" in self.prompts:
                                self.last_used_prompt_type = "food_pairing"
                                return self.prompts["food_pairing"]
                        
                        break  # Stop after checking the most recent assistant message
        
        # If semantic matcher is available, use it for new queries
        if hasattr(self, 'semantic_matcher') and self.semantic_matcher:
            prompt_id = self.semantic_matcher.match_prompt(query)
            if prompt_id in self.prompts:
                self.last_used_prompt_type = next((k for k, v in self.prompts.items() if v == prompt_id), None)
                return self.prompts[prompt_id]
        
        # Fall back to keyword matching if semantic matching isn't available or fails
        # Check for recommendation patterns
        if any(term in query_lower for term in ["recommend", "suggestion", "what wine should", "looking for a", "good wine"]):
            if "recommendations" in self.prompts:
                self.last_used_prompt_type = "recommendations"
                return self.prompts["recommendations"]
        
        # Check for food pairing patterns
        if any(term in query_lower for term in ["pair with", "pairing", "goes with", "match with", "food"]):
            if "food_pairing" in self.prompts:
                self.last_used_prompt_type = "food_pairing"
                return self.prompts["food_pairing"]
        
        # [... rest of your existing detection code ...]
        
        # Default to general sommelier prompt if available
        if "sommelier" in self.prompts:
            self.last_used_prompt_type = "sommelier"
            return self.prompts["sommelier"]
            
        # Fallback to first available prompt
        first_prompt_key = next(iter(self.prompts.keys())) if self.prompts else None
        if first_prompt_key:
            self.last_used_prompt_type = first_prompt_key
        return next(iter(self.prompts.values())) if self.prompts else None
    
    def _track_algolia_operation(self, operation_type, count=1):
        """Track an Algolia operation in metrics"""
        if operation_type not in self.current_session["algolia_operations"]:
            self.current_session["algolia_operations"][operation_type] = 0
        
        self.current_session["algolia_operations"][operation_type] += count
        self.current_session["algolia_operations"]["total_operations"] += count
        
        # You can add cost estimation based on Algolia's pricing
        # For example, if search operations cost $0.0001 each
        # operation_costs = {"search_operations": 0.0001, "get_operations": 0.0001, ...}
        # self.current_session["algolia_operations"]["operations_cost"] += operation_costs.get(operation_type, 0) * count

    def search_index(self, index_name, query, params=None):
        """Wrapper for Algolia search operation"""
        index = self.client.init_index(index_name)
        self._track_algolia_operation("search_operations")
        return index.search(query, params)

    def get_object(self, index_name, object_id):
        """Wrapper for Algolia get_object operation"""
        index = self.client.init_index(index_name)
        self._track_algolia_operation("get_operations")
        return index.get_object(object_id)

    def save_object(self, index_name, object_data):
        """Wrapper for Algolia save_object operation"""
        index = self.client.init_index(index_name)
        self._track_algolia_operation("save_operations")
        return index.save_object(object_data)

    # Add similar methods for other operations
    
    
    def log_query(self, query, is_cache_hit, response_time, query_type=None, object_id=None):
        """Log a query and update metrics"""
        self.current_session["total_queries"] += 1
        
        if is_cache_hit:
            self.current_session["cache_hits"] += 1
            self.current_session["cache_hit_times"].append(response_time)
        else:
            self.current_session["cache_misses"] += 1
            self.current_session["generation_times"].append(response_time)
        
        self.current_session["response_times"].append(response_time)
        
        # Track by query type
        if query_type:
            if query_type not in self.current_session["query_types"]:
                self.current_session["query_types"][query_type] = {
                    "total": 0, "hits": 0, "misses": 0
                }
            
            self.current_session["query_types"][query_type]["total"] += 1
            if is_cache_hit:
                self.current_session["query_types"][query_type]["hits"] += 1
            else:
                self.current_session["query_types"][query_type]["misses"] += 1
        
        # Log the query details
        query_entry = {
            "timestamp": datetime.now().isoformat(),
            "query": query[:100] + "..." if len(query) > 100 else query,  # Truncate long queries
            "cache_hit": is_cache_hit,
            "response_time": response_time,
            "query_type": query_type,
            "object_id": object_id
        }
        self.current_session["query_log"].append(query_entry)
    
    def log_error(self, error_type=None, details=None):
        """Log an API error"""
        self.current_session["api_errors"] += 1
        
        if "errors" not in self.current_session:
            self.current_session["errors"] = []
        
        error_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": error_type,
            "details": str(details)[:200] if details else None  # Truncate long error messages
        }
        self.current_session["errors"].append(error_entry)
    
    def get_session_duration(self):
        """Calculate and format the session duration"""
        start = datetime.fromisoformat(self.current_session["start_time"])
        end = datetime.now()
        duration = end - start
        
        hours, remainder = divmod(duration.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours > 0:
            return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
        elif minutes > 0:
            return f"{int(minutes)}m {int(seconds)}s"
        else:
            return f"{int(seconds)}s"
    
    def print_metrics_summary(self):
        """Print a summary of the current session metrics"""
        self.calculate_derived_metrics()
        
        print(f"\n{Fore.CYAN}=== Sommelier AI Cache Metrics Summary ==={Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Session Duration: {self.get_session_duration()}{Style.RESET_ALL}")
        print(f"Total Queries: {self.current_session['total_queries']}")
        print(f"Cache Hits: {self.current_session['cache_hits']} ({self.current_session['cache_hit_rate']}%)")
        print(f"Cache Misses: {self.current_session['cache_misses']} ({self.current_session['cache_miss_rate']}%)")

        # Add Algolia operations section
        if "algolia_operations" in self.current_session:
            print(f"\n{Fore.CYAN}Algolia API Operations:{Style.RESET_ALL}")
            ops = self.current_session["algolia_operations"]
            print(f"Total Operations: {ops['total_operations']}")
            print(f"Search Operations: {ops.get('search_operations', 0)}")
            print(f"Get Operations: {ops.get('get_operations', 0)}")
            print(f"Save Operations: {ops.get('save_operations', 0)}")
            print(f"Update Operations: {ops.get('update_operations', 0)}")
            print(f"Delete Operations: {ops.get('delete_operations', 0)}")
            if "operations_cost" in ops and ops["operations_cost"] > 0:
                print(f"Estimated API Cost: ${ops['operations_cost']:.4f}")
        
        if self.current_session["avg_response_time"] > 0:
            print(f"\nAverage Response Time: {self.current_session['avg_response_time']:.2f}s")
        if self.current_session["avg_cache_hit_time"] > 0:
            print(f"Average Cache Hit Time: {self.current_session['avg_cache_hit_time']:.2f}s")
        if self.current_session["avg_generation_time"] > 0:
            print(f"Average Generation Time: {self.current_session['avg_generation_time']:.2f}s")
        
        print(f"\n{Fore.GREEN}Estimated Cost Savings: ${self.current_session['estimated_cost_saved']:.4f}{Style.RESET_ALL}")
        print(f"Cost Without Caching: ${self.current_session['potential_cost_without_caching']:.4f}")
        print(f"Actual Cost: ${self.current_session['actual_cost_with_caching']:.4f}")
        print(f"Cost Reduction: {self.current_session['cost_reduction_percentage']}%")
        
        if self.current_session["query_types"]:
            print(f"\n{Fore.CYAN}Cache Performance by Query Type:{Style.RESET_ALL}")
            for qtype, stats in self.current_session["query_types"].items():
                hit_rate = round(stats["hits"] / stats["total"] * 100, 2) if stats["total"] > 0 else 0
                print(f"{qtype}: {hit_rate}% hit rate ({stats['hits']}/{stats['total']})")
    
    def generate_charts(self, output_dir="./metrics_charts"):
        """Generate charts visualizing the metrics data"""
        if self.current_session["total_queries"] == 0:
            print(f"{Fore.YELLOW}No data to generate charts.{Style.RESET_ALL}")
            return
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Calculate needed metrics
        self.calculate_derived_metrics()
        
        # 1. Cache Hit/Miss Pie Chart
        plt.figure(figsize=(10, 6))
        labels = ['Cache Hits', 'Cache Misses']
        sizes = [self.current_session["cache_hits"], self.current_session["cache_misses"]]
        colors = ['#4CAF50', '#F44336']
        
        plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=140)
        plt.axis('equal')
        plt.title('Cache Hit/Miss Distribution')
        plt.savefig(f"{output_dir}/cache_hit_miss_pie.png")
        plt.close()
        
        # 2. Response Time Comparison Bar Chart
        if self.current_session["avg_cache_hit_time"] > 0 and self.current_session["avg_generation_time"] > 0:
            plt.figure(figsize=(10, 6))
            
            categories = ['Cache Hit', 'New Generation']
            times = [self.current_session["avg_cache_hit_time"], self.current_session["avg_generation_time"]]
            
            plt.bar(categories, times, color=['#4CAF50', '#F44336'])
            plt.ylabel('Average Response Time (seconds)')
            plt.title('Response Time Comparison')
            
            # Add text labels above bars
            for i, v in enumerate(times):
                plt.text(i, v + 0.1, f"{v:.2f}s", ha='center')
            
            plt.savefig(f"{output_dir}/response_time_comparison.png")
            plt.close()
        
        # 3. Cost Comparison Bar Chart
        plt.figure(figsize=(10, 6))
        
        categories = ['Without Caching', 'With Caching']
        costs = [
            self.current_session["potential_cost_without_caching"],
            self.current_session["actual_cost_with_caching"]
        ]
        
        plt.bar(categories, costs, color=['#F44336', '#4CAF50'])
        plt.ylabel('Estimated Cost ($)')
        plt.title('Cost Comparison')
        
        # Add text labels above bars
        for i, v in enumerate(costs):
            plt.text(i, v + 0.001, f"${v:.4f}", ha='center')
        
        plt.savefig(f"{output_dir}/cost_comparison.png")
        plt.close()
        
        # 4. Query Type Performance (if we have query types)
        if self.current_session["query_types"]:
            plt.figure(figsize=(12, 6))
            
            types = list(self.current_session["query_types"].keys())
            hit_rates = []
            
            for qtype in types:
                stats = self.current_session["query_types"][qtype]
                hit_rate = round(stats["hits"] / stats["total"] * 100, 2) if stats["total"] > 0 else 0
                hit_rates.append(hit_rate)
            
            # Sort by hit rate
            sorted_data = sorted(zip(types, hit_rates), key=lambda x: x[1], reverse=True)
            types = [x[0] for x in sorted_data]
            hit_rates = [x[1] for x in sorted_data]
            
            plt.bar(types, hit_rates, color='#2196F3')
            plt.ylabel('Cache Hit Rate (%)')
            plt.title('Cache Performance by Query Type')
            plt.xticks(rotation=45, ha='right')
            
            # Add text labels above bars
            for i, v in enumerate(hit_rates):
                plt.text(i, v + 1, f"{v}%", ha='center')
            
            plt.tight_layout()
            plt.savefig(f"{output_dir}/query_type_performance.png")
            plt.close()
        
        print(f"{Fore.GREEN}Charts generated in {output_dir}{Style.RESET_ALL}")
    
    def export_detailed_report(self, output_file="sommelier_metrics_report.txt"):
        """Export a detailed metrics report to a text file"""
        self.calculate_derived_metrics()
        
        with open(output_file, 'w') as f:
            f.write("=== SOMMELIER AI ASSISTANT CACHE METRICS REPORT ===\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n\n")
            
            f.write("SESSION SUMMARY\n")
            f.write(f"Start Time: {self.current_session['start_time']}\n")
            if 'end_time' in self.current_session:
                f.write(f"End Time: {self.current_session['end_time']}\n")
            else:
                self.current_session['end_time'] = datetime.now().isoformat()
                f.write(f"End Time: {self.current_session['end_time']}\n")
            f.write(f"Duration: {self.get_session_duration()}\n\n")
            
            f.write("QUERY METRICS\n")
            f.write(f"Total Queries: {self.current_session['total_queries']}\n")
            f.write(f"Cache Hits: {self.current_session['cache_hits']} ({self.current_session['cache_hit_rate']}%)\n")
            f.write(f"Cache Misses: {self.current_session['cache_misses']} ({self.current_session['cache_miss_rate']}%)\n")
            f.write(f"API Errors: {self.current_session['api_errors']}\n\n")
            
            f.write("PERFORMANCE METRICS\n")
            f.write(f"Average Response Time: {self.current_session['avg_response_time']:.2f}s\n")
            if self.current_session["avg_cache_hit_time"] > 0:
                f.write(f"Average Cache Hit Time: {self.current_session['avg_cache_hit_time']:.2f}s\n")
            if self.current_session["avg_generation_time"] > 0:
                f.write(f"Average Generation Time: {self.current_session['avg_generation_time']:.2f}s\n")
            if self.current_session["avg_cache_hit_time"] > 0 and self.current_session["avg_generation_time"] > 0:
                speedup = self.current_session["avg_generation_time"] / self.current_session["avg_cache_hit_time"]
                f.write(f"Cache Speedup Factor: {speedup:.2f}x\n\n")
            
            f.write("COST METRICS\n")
            f.write(f"Estimated Cost per 1K Tokens: ${self.estimated_cost_per_1k_tokens}\n")
            f.write(f"Estimated Tokens per Response: {self.estimated_tokens_per_response}\n")
            f.write(f"Estimated Tokens Saved: {self.current_session['estimated_tokens_saved']}\n")
            f.write(f"Estimated Cost Saved: ${self.current_session['estimated_cost_saved']:.4f}\n")
            f.write(f"Potential Cost Without Caching: ${self.current_session['potential_cost_without_caching']:.4f}\n")
            f.write(f"Actual Cost With Caching: ${self.current_session['actual_cost_with_caching']:.4f}\n")
            f.write(f"Cost Reduction: {self.current_session['cost_reduction_percentage']}%\n\n")
            
            if self.current_session["query_types"]:
                f.write("QUERY TYPE PERFORMANCE\n")
                for qtype, stats in self.current_session["query_types"].items():
                    hit_rate = round(stats["hits"] / stats["total"] * 100, 2) if stats["total"] > 0 else 0
                    f.write(f"{qtype}: {hit_rate}% hit rate ({stats['hits']}/{stats['total']})\n")
                f.write("\n")
            
            f.write("RECENT QUERIES\n")
            for i, entry in enumerate(reversed(self.current_session["query_log"][-10:])):
                result = "HIT" if entry["cache_hit"] else "MISS"
                f.write(f"{i+1}. [{result}] {entry['query']} - {entry['response_time']:.2f}s\n")
            
            if "errors" in self.current_session and self.current_session["errors"]:
                f.write("\nERRORS\n")
                for i, error in enumerate(self.current_session["errors"]):
                    f.write(f"{i+1}. [{error['timestamp']}] {error['type']}: {error['details']}\n")
        
        print(f"{Fore.GREEN}Detailed report saved to {output_file}{Style.RESET_ALL}")
    
    def reset_metrics(self):
        """Reset metrics for a new session"""
        # Save current session before resetting
        self.save_metrics()
        
        # Initialize new session
        self.current_session = {
            "start_time": datetime.now().isoformat(),
            "total_queries": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "api_errors": 0,
            "response_times": [],
            "cache_hit_times": [],
            "generation_times": [],
            "query_types": {},
            "query_log": [],
            "algolia_operations": {
                "search_operations": 0,
                "get_operations": 0, 
                "browse_operations": 0,
                "save_operations": 0,
                "update_operations": 0,
                "delete_operations": 0,
                "total_operations": 0,
                "operations_cost": 0.0
            }
        }
        print(f"{Fore.GREEN}Metrics reset for new session{Style.RESET_ALL}")
    
    # Assistant methods
    def _setup(self):
        """Set up data sources and prompts for the assistant"""
        print(f"{Fore.CYAN}Setting up Sommelier Assistant for index: {self.index_name}{Style.RESET_ALL}")
        
        # Set up data sources
        self._setup_data_sources()
        
        # Set up prompts
        self._setup_prompts()
        
        print(f"{Fore.GREEN}Sommelier Assistant is ready to serve!{Style.RESET_ALL}")
    
    def _setup_data_sources(self):
        """Set up data sources for different wine categories"""
        print(f"{Fore.CYAN}Setting up data sources...{Style.RESET_ALL}")
        
        # First, retrieve all existing data sources
        existing_data_sources = self.list_data_sources()
        print(f"Found {len(existing_data_sources)} existing data sources")
        
        # Define data sources we need
        data_source_configs = [
            {"name": "All Wines", "key": "all_wines", "filters": None},
            {"name": "Red Wines", "key": "red_wines", "filters": "type_id:1"},
            {"name": "White Wines", "key": "white_wines", "filters": "type_id:2"},
            {"name": "Sparkling Wines", "key": "sparkling_wines", "filters": "type_id:3"},
            {"name": "Rosé Wines", "key": "rose_wines", "filters": "type_id:4"},
            {"name": "Premium Wines", "key": "premium_wines", "filters": "average_rating>=4.0"}
        ]
        
        # Set up each data source
        for config in data_source_configs:
            name = config["name"]
            key = config["key"]
            filters = config["filters"]
            
            # Check if this data source already exists
            existing_ds = self._find_existing_data_source(existing_data_sources, name, filters)
            
            if existing_ds:
                print(f"Using existing data source: {name} (ID: {existing_ds.get('objectID')})")
                self.data_sources[key] = existing_ds.get("objectID")
            else:
                # Create a new data source
                new_ds = self.create_data_source(
                    name=name, 
                    source_index=self.index_name,
                    filters=filters
                )
                if new_ds:
                    self.data_sources[key] = new_ds.get("objectID")
    
    def _find_existing_data_source(self, data_sources, name, filters):
        """Find an existing data source by name and filters"""
        for ds in data_sources:
            # Match by name
            if ds.get("name") == name:
                # Check filters if applicable
                ds_filters = ds.get("filters")
                if (filters is None and ds_filters is None) or filters == ds_filters:
                    return ds
        return None
    def _calculate_text_similarity(self, text1, text2):
        """Calculate similarity between two text strings"""
        # Convert to sets of words for a simple Jaccard similarity
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        # Jaccard similarity: intersection / union
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union

    def _setup_prompts(self):
        """Set up prompts for different sommelier functions"""
        print(f"{Fore.CYAN}Setting up sommelier prompts...{Style.RESET_ALL}")
        
        # First, retrieve all existing prompts
        existing_prompts = self.list_prompts()
        print(f"Found {len(existing_prompts)} existing prompts")
        
        # Define our prompt configurations
        prompt_configs = [
            {
                "name": "Sommelier Assistant",
                "key": "sommelier",
                "instructions": """
                You are a sophisticated sommelier AI assistant with deep knowledge of wines, vineyards, and wine culture.
                
                Use the provided wine database to answer questions, make recommendations, and educate the user about wines.
                Speak in a friendly, knowledgeable tone that blends expertise with approachability.
                
                When recommending wines:
                - Consider user preferences (tastes, price range, occasion)
                - Suggest specific wines from the database
                - Explain why you're recommending them
                - Provide context about the winery, region, or vintage when relevant
                
                When providing wine education:
                - Be thorough but accessible
                - Explain wine terminology in layman's terms when appropriate
                - Share interesting facts or stories that enrich the user's understanding
                
                When discussing food pairings:
                - Explain the principles behind the pairing
                - Consider both the wine's profile and the food's characteristics
                - Suggest specific wines from the database that would pair well
                
                When evaluating wines:
                - Cover aspects like taste profile, quality, value, and aging potential
                - Use specific data from the wine database when available
                - Provide context about what makes the wine unique or notable
                
                For taste profiles, always explain:
                - Primary tastes: From the grape (fruit, floral, herb flavors)
                - Secondary tastes: From winemaking process (fermentation)
                - Tertiary tastes: From aging, oxidation, and oak influence
                
                When providing value assessments, include:
                - Price tier (budget, mid-range, premium, luxury)
                - Value rating relative to similar wines
                - Factors that justify the price point
                
                For aging potential:
                - Recommend ideal drinking windows
                - Explain how the wine might evolve over time
                - Indicate whether it's meant for immediate consumption or cellaring
                
                For serving recommendations:
                - Specific temperature ranges in Celsius and Fahrenheit
                - Decanting time if applicable
                - Ideal glass shape and style
                - Aeration needs
                
                For vintage variations:
                - Explain weather and climate factors affecting specific vintages
                - Compare different vintages when relevant
                - Highlight exceptional years
                
                For grape information:
                - Explain characteristics of grape varieties
                - Discuss where they grow best and why
                - Highlight historical and cultural significance
                
                Always be helpful, accurate, and focused on enhancing the user's wine experience.
                Use concrete examples from the database whenever possible.
                
                Maintain conversation history to provide consistent, contextual responses.
                """
            },
            {
                "name": "Wine Recommendations",
                "key": "recommendations",
                "instructions": """
                You are a sommelier specializing in wine recommendations. Based on the user's preferences, occasion, and any other relevant factors, recommend specific wines from the database.
                
                For each recommendation:
                1. Provide the wine name, winery, region, and vintage
                2. Explain why you're recommending this specific wine
                3. Describe its taste profile, highlighting primary, secondary, and tertiary tastes
                4. Mention price range and value assessment
                5. Suggest ideal serving conditions
                
                If the user hasn't provided enough information for personalized recommendations, ask follow-up questions about:
                - Preferred taste profiles (e.g., fruit-forward, earthy, tannic, acidic)
                - Price range
                - Wine type preferences (red, white, sparkling, etc.)
                - Occasion or food pairing needs
                
                When discussing taste profiles, always explain:
                - Primary tastes: From the grape (fruit, floral, herb flavors)
                - Secondary tastes: From winemaking process (fermentation)
                - Tertiary tastes: From aging, oxidation, and oak influence
                
                Use data from the wine database to make specific, personalized recommendations. 
                Aim to recommend 3-5 wines that best match the user's preferences.
                
                Always explain your recommendations in a way that helps the user understand why these wines would appeal to them.
                
                Maintain conversation history to provide consistent, contextual responses.
                """
            },
            {
                "name": "Food and Wine Pairing",
                "key": "food_pairing",
                "instructions": """
                You are a sommelier specializing in food and wine pairings. Help the user find the perfect wine to complement their meal or the perfect food to enjoy with a particular wine.
                
                When suggesting pairings:
                1. Explain the principles behind the pairing (e.g., complementary flavors, matching intensity)
                2. Suggest specific wines from the database that would pair well with the food
                3. For each suggested wine, explain why it pairs well with the food
                4. Consider the preparation method, sauces, and dominant flavors of the food
                
                If the user mentions a specific wine, suggest foods that would pair well with it.
                If the user mentions a specific dish or cuisine, suggest wines that would pair well.
                
                Always provide the reasoning behind your suggestions to help educate the user about pairing principles.
                
                Use the wine database to recommend specific wines with their details:
                - Name, winery, vintage
                - Taste profile (primary, secondary, tertiary flavors)
                - Structure (body, acidity, tannins)
                
                Be specific and precise in your suggestions, avoiding generic advice when possible.
                
                Maintain conversation history to provide consistent, contextual responses.
                """
            },
            {
                "name": "Wine Education",
                "key": "education",
                "instructions": """
                You are a wine educator helping users understand wine terminology, production methods, regions, grape varieties, and culture.
                
                When providing wine education:
                1. Be thorough but accessible in your explanations
                2. Explain wine terminology in layman's terms when appropriate
                3. Share interesting facts or stories that enrich the user's understanding
                4. Use examples from the wine database to illustrate concepts
                5. Progressively build the user's knowledge by connecting new concepts to ones previously explained
                
                For questions about tastes and flavors:
                - Clearly explain the difference between primary, secondary, and tertiary tastes
                - Primary: fruit, floral, and herb flavors that come directly from the grape
                - Secondary: flavors from fermentation and winemaking processes
                - Tertiary: flavors developed through aging, such as vanilla from oak
                
                For questions about wine regions:
                - Explain the characteristics of the region (climate, soil, traditions)
                - Describe typical wines from the region
                - Mention notable wineries from the database
                
                For questions about grape varieties:
                - Describe typical flavor profiles
                - Mention regions where the variety thrives
                - Suggest specific wines from the database that showcase the variety
                
                For questions about winemaking:
                - Explain different production methods and their effects on wine
                - Contrast traditional and modern approaches
                - Discuss how production influences taste and quality
                
                Always adapt your explanation's complexity based on the user's apparent knowledge level.
                
                Maintain conversation history to provide consistent, contextual responses.
                """
            },
            {
                "name": "Vineyard and Winery Information",
                "key": "vineyard_info",
                "instructions": """
                You are a sommelier with expertise in vineyard and winery information. Provide detailed information about vineyards, wineries, and their wines.
                
                When discussing vineyards and wineries:
                1. Share history and background of the winery/vineyard
                2. Describe the terroir (soil, climate, topography) and explain its impact on the wines
                3. Discuss winemaking techniques and philosophies
                4. Highlight notable wines from the winery in the database
                5. Mention any unique or distinguishing characteristics
                
                Address factors like:
                - Soil profiles and mineral content
                - Climate and weather patterns
                - Sustainable or biodynamic practices
                - Winemaker background and approach
                - Cultural and historical context
                
                For soil information, include:
                - Soil types and composition
                - Drainage characteristics
                - Mineral content
                - How the soil affects the wine's character
                
                For weather and climate information, include:
                - Climate type (Mediterranean, Continental, etc.)
                - Temperature patterns
                - Rainfall patterns
                - How weather impacts vintages
                
                For historical context, include:
                - Winery history
                - Regional traditions
                - Winemaking heritage
                - Historical significance of the wine style
                
                Use the wine database to reference specific wines and their characteristics.
                Be educational and informative, helping the user appreciate how these factors influence wine quality and character.
                
                Maintain conversation history to provide consistent, contextual responses.
                """
            },
            {
                "name": "Wine Tasting Guide",
                "key": "tasting",
                "instructions": """
                You are a sommelier guiding users through wine tasting experiences and helping them understand how to evaluate wines.
                
                Provide guidance on:
                1. How to properly taste wine (look, smell, taste, finish)
                2. How to identify and describe different flavors and characteristics
                3. How to evaluate wine quality, balance, complexity, and structure
                4. Proper serving techniques, temperatures, and glassware
                
                When describing specific wines from the database:
                - Use the wine's actual taste profile data when available
                - Describe appearance, aroma, palate, and finish
                - Highlight distinctive characteristics
                - Suggest what to look for when tasting this particular wine
                
                For quality assessment, always cover:
                - Balance: Harmony among components (acidity, tannins, alcohol, fruit)
                - Intensity: Concentration of flavors and aromas
                - Clarity: Definition and precision of flavors
                - Complexity: Range of different flavors and nuances
                - Typicity: How well the wine represents its variety and region
                
                For serving recommendations, include:
                - Serving temperature range (Celsius and Fahrenheit)
                - Decanting time if needed
                - Glass type recommendations
                - Aeration needs
                - Optimal drinking window
                
                Help users develop their palate by:
                - Explaining how to identify specific tastes (primary, secondary, tertiary)
                - Relating flavors to common foods or experiences
                - Building wine vocabulary progressively
                - Suggesting comparative tastings
                
                Be encouraging and non-judgmental, emphasizing that taste is subjective while still providing expert guidance.
                
                Maintain conversation history to provide consistent, contextual responses.
                """
            }
        ]
        
        # Set up each prompt
        for config in prompt_configs:
            name = config["name"]
            key = config["key"]
            instructions = config["instructions"]
            
            # Check if this prompt already exists
            existing_prompt = self._find_existing_prompt(existing_prompts, name)
            
            if existing_prompt:
                print(f"Using existing prompt: {name} (ID: {existing_prompt.get('objectID')})")
                self.prompts[key] = existing_prompt.get("objectID")
                # Store the instructions for semantic matcher
                self.prompt_instructions[key] = instructions
            else:
                # Create a new prompt
                new_prompt = self.create_prompt(
                    name=name,
                    instructions=instructions
                )
                if new_prompt:
                    self.prompts[key] = new_prompt.get("objectID")
                    # Store the instructions for semantic matcher
                    self.prompt_instructions[key] = instructions
    
    def _find_existing_prompt(self, prompts, name):
        """Find an existing prompt by name"""
        for prompt in prompts:
            if prompt.get("name") == name:
                return prompt
        return None

    def create_data_source(self, name, source_index, filters=None):
        """Create a data source using an existing Algolia index"""
        # First check if a data source with this name and filters already exists
        existing_sources = self.list_data_sources()
        for source in existing_sources:
            if source.get("name") == name:
                # Check if filters match
                source_filters = source.get("filters")
                if (filters is None and source_filters is None) or filters == source_filters:
                    print(f"Data source '{name}' already exists with ID: {source.get('objectID')}")
                    return source
        
        # If we get here, we need to create a new data source
        endpoint = f"{self.base_url}/create/data_source"
        
        data = {
            "name": name,
            "source": source_index
        }
        
        if filters:
            data["filters"] = filters
            
        try:
            response = requests.post(endpoint, headers=self.headers, json=data)
            
            if response.status_code == 409:
                print(f"Data source '{name}' creation returned conflict status, but couldn't find it in the list")
                # Since we already checked above, this shouldn't happen often
                # But return a placeholder just in case
                return {"objectID": f"unknown_id_for_{name}", "name": name}
            
            response.raise_for_status()
            print(f"Successfully created data source: {name}")
            return response.json()
        except Exception as e:
            print(f"Error creating data source: {e}")
            if 'response' in locals() and hasattr(response, 'text'):
                print(f"Response: {response.text}")
            return None
    
    def create_prompt(self, name, instructions, tone="natural"):
        """Create a prompt for the GenAI Toolkit"""
        # First check if a prompt with this name already exists
        existing_prompts = self.list_prompts()
        for prompt in existing_prompts:
            if prompt.get("name") == name:
                print(f"Prompt '{name}' already exists with ID: {prompt.get('objectID')}")
                return prompt
        
        # If we get here, we need to create a new prompt
        endpoint = f"{self.base_url}/create/prompt"
        
        data = {
            "name": name,
            "instructions": instructions,
            "tone": tone
        }
        
        try:
            response = requests.post(endpoint, headers=self.headers, json=data)
            
            if response.status_code == 409:
                print(f"Prompt '{name}' creation returned conflict status, but couldn't find it in the list")
                # Since we already checked above, this shouldn't happen often
                # But return a placeholder just in case
                return {"objectID": f"unknown_id_for_{name}", "name": name}
            
            response.raise_for_status()
            print(f"Successfully created prompt: {name}")
            return response.json()
        except Exception as e:
            print(f"Error creating prompt: {e}")
            if 'response' in locals() and hasattr(response, 'text'):
                print(f"Response: {response.text}")
            return None
    
    def list_data_sources(self):
        """List all data sources"""
        try:
            data_sources = []
            # Use search with an empty query instead of browse_objects
            results = self.search_index("algolia_rag_data_sources", '', {
                'hitsPerPage': 1000  # Get up to 1000 data sources
            })
            
            if 'hits' in results:
                data_sources = results['hits']
            
            return data_sources
        except Exception as e:
            print(f"Error listing data sources: {e}")
            return []
    
    def list_prompts(self):
        """List all prompts"""
        try:
            prompts = []
            # Use search with an empty query instead of browse_objects
            results = self.search_index("algolia_rag_prompts", '', {
                'hitsPerPage': 1000  # Get up to 1000 prompts
            })
            
            if 'hits' in results:
                prompts = results['hits']
            
            return prompts
        except Exception as e:
            print(f"Error listing prompts: {e}")
            return []
    
    def find_previous_response(self, query, data_source_id, prompt_id):
        """
        Enhanced method to find a previously saved response by using flexible text matching
        to overcome prompt ID mismatches and other inconsistencies.
        
        Args:
            query: The user's query
            data_source_id: The data source ID used for the query
            prompt_id: The prompt ID used for the query
                    
        Returns:
            The previous response object if found, None otherwise
        """
        try:
            # Normalize the query for better matching
            normalized_query = query.lower().strip()
            user_query_only = normalized_query
            
            # Remove context/conversation markers if present
            if "user:" in normalized_query:
                parts = normalized_query.split("user:")
                user_query_only = parts[-1].strip()
            
            if self.debug:
                print(f"{Fore.CYAN}Looking for response to query: '{user_query_only}'{Style.RESET_ALL}")
                print(f"{Fore.CYAN}Using data source: {data_source_id}{Style.RESET_ALL}")
            
            # First try the direct object ID lookup for backward compatibility
            query_essence = self._get_query_essence(query)
            object_id = self._generate_stable_id(query_essence, data_source_id, prompt_id)
            
            if self.debug:
                print(f"{Fore.CYAN}Trying direct lookup with objectID: {object_id}{Style.RESET_ALL}")
            
            try:
                direct_result = self.get_object("algolia_rag_responses", object_id)
                print(f"{Fore.GREEN}Found direct cache hit with objectID: {object_id}{Style.RESET_ALL}")
                return direct_result
            except Exception as e:
                if self.debug:
                    print(f"{Fore.YELLOW}No direct object match: {e}{Style.RESET_ALL}")
            
            # MAIN IMPROVEMENT: Use text-based search focusing on the query content
            # rather than exact object ID or prompt ID matching
            print(f"{Fore.CYAN}Searching for similar queries in response index...{Style.RESET_ALL}")
            
            # Search by the actual query text with data source filter only
            results = self.search_index("algolia_rag_responses", user_query_only, {
                'hitsPerPage': 10,
                'filters': f"dataSourceID:{data_source_id}",  # Only filter by data source, not prompt
                'typoTolerance': True,  # Allow for typos/fuzzy matching
                'attributesToRetrieve': ['query', 'response', 'conversationID', 'promptID', 'objectID', 'createdAt']
            })
            
            if self.debug:
                print(f"{Fore.CYAN}Search returned {len(results.get('hits', []))} results{Style.RESET_ALL}")
            
            # If we found results, look for the best match
            if results.get('hits') and len(results.get('hits')) > 0:
                # Find the best matching query
                best_match = None
                best_score = 0.7  # Minimum threshold for similarity
                
                for hit in results.get('hits'):
                    hit_query = hit.get('query', '').lower().strip()
                    
                    # Extract the user part from context if present
                    if "user:" in hit_query:
                        parts = hit_query.split("user:")
                        hit_user_query = parts[-1].strip()
                    else:
                        hit_user_query = hit_query
                    
                    # Calculate similarity score
                    similarity = self._calculate_text_similarity(user_query_only, hit_user_query)
                    
                    if self.debug:
                        print(f"{Fore.CYAN}Comparing '{user_query_only}' with '{hit_user_query}', similarity: {similarity:.2f}{Style.RESET_ALL}")
                    
                    # If the similarity exceeds our threshold and is better than previous matches
                    if similarity > best_score:
                        best_score = similarity
                        best_match = hit
                
                if best_match:
                    print(f"{Fore.GREEN}Found cached response with {best_score:.2f} similarity{Style.RESET_ALL}")
                    return best_match
                    
            # If no good match is found, try more specialized searches
            
            # Special handling for food pairing queries
            if self._is_food_pairing_query(normalized_query):
                food_keywords = self._extract_food_items(normalized_query)
                if food_keywords:
                    search_query = " ".join(food_keywords)
                    print(f"{Fore.CYAN}Food pairing query detected, trying food terms: {search_query}{Style.RESET_ALL}")
                    
                    # Search specifically with food terms
                    food_results = self.search_index("algolia_rag_responses", search_query, {
                        'hitsPerPage': 5,
                        'filters': f"dataSourceID:{data_source_id}",
                        'typoTolerance': True
                    })
                    
                    if food_results.get('hits') and len(food_results.get('hits')) > 0:
                        # Return the best match (newest one)
                        best_food_match = sorted(food_results.get('hits'), 
                                            key=lambda x: x.get('createdAt', ''), 
                                            reverse=True)[0]
                        print(f"{Fore.GREEN}Found food pairing match from {best_food_match.get('createdAt')}{Style.RESET_ALL}")
                        return best_food_match
            
            print(f"{Fore.YELLOW}No suitable cached response found{Style.RESET_ALL}")
            return None
            
        except Exception as e:
            print(f"{Fore.RED}Error searching for previous responses: {e}{Style.RESET_ALL}")
            if self.debug:
                import traceback
                traceback.print_exc()
            return None
    
    def _extract_food_items(self, query):
        """Extract food items from a pairing query with expanded categories and improved validation"""
        # Clean the query first - remove any conversation artifacts
        # Add better validation for follow-up queries
        if "option" in query.lower() or "sounds good" in query.lower() or any(word in query.lower() for word in ["that wine", "that option"]):
            # Don't attempt to extract food items from follow-up queries
            return []
        query = query.lower().strip()

        # Check for follow-up indicators that reference previous suggestions
        if any(phrase in query for phrase in ["first suggestion", "second suggestion", "third suggestion", 
                                         "that suggestion", "option", "sounds good"]):
            if self.debug:
                print(f"{Fore.CYAN}Detected a follow-up about previous suggestions{Style.RESET_ALL}")
            return []  # Don't attempt to extract food items
        
        # Reject any suspicious tokens that might be from conversation context
        suspicious_tokens = ["assistant:", "user:", "assistant", "user", "sommelier:"]
        for token in suspicious_tokens:
            if token in query:
                query = query.replace(token, "")
        
        # Major food categories to look for (expanded)
        food_categories = [
            # Meats
            "steak", "beef", "pork", "lamb", "veal", "chicken", "turkey", "duck", "goose", 
            "meat", "burgers", "barbecue", "bbq", "ribs", "bacon", "ham", "sausage",
            # Seafood
            "fish", "salmon", "tuna", "cod", "halibut", "trout", "seafood", "shrimp", "lobster", 
            "crab", "oyster", "mussel", "clam", "scallop", "squid", "octopus", "eel",
            # Italian
            "pasta", "pizza", "risotto", "lasagna", "spaghetti", "gnocchi", "ravioli",
            # Cheese and dairy
            "cheese", "cheddar", "brie", "camembert", "gouda", "blue cheese", "goat cheese", 
            "parmesan", "feta", "mozzarella", "ricotta", "dairy",
            # Desserts
            "chocolate", "dessert", "cake", "pie", "tart", "cookie", "pudding", "ice cream",
            # Vegetables
            "vegetable", "salad", "greens", "tomato", "mushroom", "truffle", "potato", 
            "eggplant", "zucchini", "cucumber", "carrot", "asparagus", "broccoli",
            # Cuisines
            "italian", "french", "indian", "chinese", "japanese", "mexican", "thai", "spanish"
        ]
        
        # Check for explicit food mentions
        found_foods = []
        
        for food in food_categories:
            if food in query:  # Use lowercase comparison for better matching
                found_foods.append(food)
        
        # If none found, look for food terms after "with" in pairing questions
        if not found_foods and ("pair" in query or "pairing" in query):
            # "what wine pairs with X" pattern
            parts = query.split("with")
            if len(parts) > 1:
                after_with = parts[1].strip()
                # Take the first few words after "with" as probable food
                food_part = " ".join(after_with.split()[:3])
                # Validate the food part - only include if it doesn't have suspicious tokens
                if not any(token in food_part for token in suspicious_tokens):
                    found_foods.append(food_part)
        
        # Special handling for follow-up questions about "that" or "this"
        if not found_foods and ("that" in query or "this" in query) and ("pair" in query or "dish" in query or "food" in query):
            # For follow-up questions like "what dishes pair well with that?"
            # Avoid extracting just "that" or "this" as they cause filter issues
            return []  # Return empty list to avoid problematic filters
        
        # Final validation - remove any items that are empty, have punctuation, or are just pronouns
        cleaned_foods = []
        pronouns = ["that", "this", "these", "those", "it"]
        for food in found_foods:
            # Remove any punctuation at the end
            food = food.rstrip('.,?!:;')
            # Skip single pronouns or empty strings
            if not food.strip() or food.strip() in pronouns:
                continue
            cleaned_foods.append(food)
        
        return cleaned_foods
    
    def _extract_key_terms(self, query):
        """Extract the most important terms from a query with improved precision"""
        # Break into words
        words = query.split()
        
        # Expanded stopwords list
        stopwords = {
            "what", "which", "how", "is", "are", "the", "a", "an", "in", "with", "for", "to", 
            "of", "would", "should", "could", "will", "can", "do", "does", "has", "have", "had",
            "i", "you", "he", "she", "we", "they", "it", "this", "that", "these", "those",
            "am", "is", "are", "was", "were", "be", "been", "being", "there", "their", "me",
            "and", "or", "but", "if", "then", "so", "because", "since", "while", "when", "where",
            "why", "how", "all", "any", "both", "each", "few", "more", "most", "other", "some",
            "such", "no", "nor", "not", "only", "own", "same", "than", "too", "very", "just",
            "should", "now", "also", "very", "really", "quite"
        }
        
        # Domain-specific stopwords (common in wine queries but don't distinguish meaning)
        wine_stopwords = {
            "wine", "wines", "drink", "bottle", "glass", "recommend", "suggestion", 
            "taste", "flavor", "recommend", "tell", "about", "know", "like", "good"
        }
        
        # Wine domain specific important terms (boosted in weighting)
        important_terms = {
            "cabernet", "merlot", "chardonnay", "pinot", "sauvignon", "riesling", "shiraz",
            "zinfandel", "syrah", "malbec", "champagne", "prosecco", "bordeaux", "burgundy",
            "vintage", "terroir", "tannin", "acidity", "oak", "body", "dry", "sweet", "pairing",
            "decant", "cellar", "sommelier", "vineyard", "winery", "german", "french", "italian", "spanish"
        }
        
        # Weight words more intelligently
        weighted_words = []
        for i, word in enumerate(words):
            word_lower = word.lower()
            # Skip stopwords
            if word_lower in stopwords:
                continue
                
            # Skip short words
            if len(word_lower) <= 2:
                continue
                
            # Base weight calculation
            weight = 1.0
            
            # Domain-specific adjustments
            if word_lower in wine_stopwords and len(words) > 3:
                weight = 0.5
            elif word_lower in important_terms:
                weight = 2.0  # Boost important wine terms
                
            # Words later in the sentence often contain the important subject
            position_factor = (i + 1) / len(words)  # 0.0 to 1.0
            weight += position_factor
                
            weighted_words.append((word_lower, weight))
        
        # Sort by weight descending
        weighted_words.sort(key=lambda x: x[1], reverse=True)
        
        # Take top words (up to 5)
        top_words = [word for word, _ in weighted_words[:5]]
        
        # If we have no words, use the full query
        if not top_words:
            return query
            
        # Join top words
        key_terms = " ".join(top_words)
        
        if self.debug:
            print(f"{Fore.CYAN}Extracted key terms: {key_terms} (from '{query}'){Style.RESET_ALL}")
        
        return key_terms
    
    def process_query(self, query, prompt_type=None, stream=False, callback=None, conversation_id=None):
        """
        Process a user query and generate a sommelier response with improved error handling
        """
        # Record start time for metrics
        start_time = time.time()

        try:
            # Set conversation ID if provided
            if conversation_id:
                self.conversation_id = conversation_id
                print(f"{Fore.CYAN}Continuing conversation with ID: {conversation_id}{Style.RESET_ALL}")
            
            # For follow-up questions in a conversation, try to detect the correct prompt type
            if self.conversation_id and not prompt_type:
                # If this is a follow-up in a conversation, try to infer the prompt type from content
                prompt_type = self._infer_prompt_type_from_query(query)
            
            # Select appropriate prompt based on query or specified type
            prompt_id = self._select_prompt(query, prompt_type)
            
            # Select appropriate data source based on query
            data_source_id = self._select_data_source(query)
            
            # Build conversation context
            context = self._build_conversation_context()
            
            # Keep query short to stay under 512 byte limit
            # Truncate user query if needed
            max_query_length = 450  # Allow some buffer for the context
            if len(query) > max_query_length:
                query = query[:max_query_length] + "..."
            
            full_query = f"{context}\n\nUser: {query}"
            
            # Double-check that the final query is within limits
            if len(full_query.encode('utf-8')) > 512:
                # If still too long, use a minimal query
                full_query = f"User: {query}"
                
            print(f"{Fore.YELLOW}Using prompt: {prompt_type or 'auto'}, data source: {data_source_id}{Style.RESET_ALL}")
            
            # For matching similar queries in the cache
            query_essence = self._get_query_essence(query)
            object_id = self._generate_stable_id(query_essence, data_source_id, prompt_id)
            
            if self.debug:
                print(f"{Fore.CYAN}Query essence: {query_essence}{Style.RESET_ALL}")
                print(f"{Fore.CYAN}Using object ID: {object_id}{Style.RESET_ALL}")
            
            # Check for a matching previous response
            previous_response = self.find_previous_response(query, data_source_id, prompt_id)
            
            # Track if this is a cache hit
            is_cache_hit = previous_response is not None
            
            # If a previous response exists, use it
            if previous_response:
                print(f"{Fore.GREEN}Using cached response{Style.RESET_ALL}")
                response_text = previous_response.get("response", "")
                
                # Update conversation ID if available
                if "conversationID" in previous_response and not self.conversation_id:
                    self.conversation_id = previous_response.get("conversationID")
                
                # Add to conversation history
                self.conversation_history.append({
                    "role": "user",
                    "content": query
                })
                self.conversation_history.append({
                    "role": "assistant",
                    "content": response_text
                })
                
                # Calculate response time for metrics
                response_time = time.time() - start_time
                
                # Log in metrics
                self.log_query(
                    query=query,
                    is_cache_hit=True,
                    response_time=response_time,
                    query_type=prompt_type or "auto",
                    object_id=object_id
                )
                
                return {
                    "response": response_text,
                    "conversationID": self.conversation_id
                }
            
            # Always use non-streaming for reliability with stable object ID
            print(f"{Fore.GREEN}Generating new response{Style.RESET_ALL}")
            response_data = self.generate_response(
                query=full_query,
                data_source_id=data_source_id,
                prompt_id=prompt_id,
                object_id=object_id
            )
            
            if not response_data:
                # Log the error in metrics
                self.log_error(
                    error_type="No Response",
                    details="Failed to generate response"
                )
                return {
                    "response": "I'm sorry, I couldn't generate a response. Please try again.",
                    "conversationID": self.conversation_id
                }
            
            # Extract response text
            response_text = response_data.get("response", "")
            
            # Store conversation ID if provided
            if "conversationID" in response_data and response_data["conversationID"]:
                self.conversation_id = response_data["conversationID"]
                print(f"{Fore.CYAN}Conversation ID: {self.conversation_id}{Style.RESET_ALL}")
            
            # Add to conversation history
            self.conversation_history.append({
                "role": "user",
                "content": query
            })
            self.conversation_history.append({
                "role": "assistant",
                "content": response_text
            })
            
            # Calculate response time for metrics
            response_time = time.time() - start_time
            
            # Log in metrics
            self.log_query(
                query=query,
                is_cache_hit=False,
                response_time=response_time,
                query_type=prompt_type or "auto",
                object_id=object_id
            )
            
            return {
                "response": response_text,
                "conversationID": self.conversation_id
            }
            
        except Exception as e:
            # Log the error
            error_message = str(e)
            self.log_error(error_type="Query Processing Error", details=error_message)
            print(f"{Fore.RED}Error processing query: {error_message}{Style.RESET_ALL}")
            
            # Calculate response time for metrics even for errors
            response_time = time.time() - start_time
            
            # Return a more helpful error message based on the error type
            if "filters:" in error_message:
                # This is likely a filter parsing error (as in your logs)
                response = "I'm having trouble understanding the context of your follow-up question. Could you please provide more details about what you're asking about specifically?"
            elif "rate limit" in error_message.lower():
                response = "I'm currently experiencing high demand. Please try again in a moment."
            elif "timeout" in error_message.lower():
                response = "It's taking longer than expected to process your request. Could you try asking in a simpler way?"
            else:
                # Generic error message for other issues
                response = "I encountered an issue while processing your question. Could you try rephrasing or asking a new question?"
            
            # Log this as a miss in metrics
            self.log_query(
                query=query,
                is_cache_hit=False,
                response_time=response_time,
                query_type=prompt_type or "auto",
                object_id=None
            )
            
            return {
                "response": response,
                "conversationID": self.conversation_id  # Return existing conversation ID even on error
            }
    
    def _select_data_source(self, query):
        """Select the appropriate data source based on query content"""
        query_lower = query.lower()
        
        # Check for wine type mentions
        if "red" in query_lower and "red_wines" in self.data_sources:
            return self.data_sources["red_wines"]
        elif "white" in query_lower and "white_wines" in self.data_sources:
            return self.data_sources["white_wines"]
        elif any(term in query_lower for term in ["sparkling", "champagne", "prosecco", "bubbly"]) and "sparkling_wines" in self.data_sources:
            return self.data_sources["sparkling_wines"]
        elif any(term in query_lower for term in ["rosé", "rose"]) and "rose_wines" in self.data_sources:
            return self.data_sources["rose_wines"]
        elif any(term in query_lower for term in ["premium", "expensive", "high quality", "best"]) and "premium_wines" in self.data_sources:
            return self.data_sources["premium_wines"]
        
        # Default to all wines
        return self.data_sources.get("all_wines")
    
    def _build_conversation_context(self):
        """Build context from conversation history with improved context retention"""
        if not self.conversation_history:
            return "You are a knowledgeable sommelier AI assistant. This is the start of a new conversation."
        
        # For Algolia GenAI Toolkit, we need to keep the context very short due to the 512 byte limit
        # Include just the last exchange (last user question and assistant response)
        # This provides crucial context for follow-up questions while staying under the limit
        context = "You are a knowledgeable sommelier AI assistant. Continue the conversation naturally."
        
        # Get the most recent exchange (up to 2 messages)
        recent_messages = self.conversation_history[-2:] if len(self.conversation_history) >= 2 else self.conversation_history
        
        # Add them to the context with role labels
        for msg in recent_messages:
            # Truncate very long messages to stay under byte limit
            content = msg['content']
            if len(content) > 100:  # Adjust this threshold as needed
                content = content[:97] + "..."
                
            context += f"\n{msg['role'].capitalize()}: {content}"
        
        # Check if the context is too large
        if len(context.encode('utf-8')) > 450:  # Leave some buffer below 512 byte limit
            # If too large, just use a simpler context
            return "You are a knowledgeable sommelier AI assistant. Continue the conversation naturally based on previous messages about wine."
        
        return context
    
    def generate_response(self, query, data_source_id, prompt_id, object_id=None):
        """Generate a response using the GenAI Toolkit with improved conversation handling"""
        endpoint = f"{self.base_url}/generate/response"
        
        # Generate a conversation ID if we don't have one yet
        if not self.conversation_id:
            import uuid
            self.conversation_id = f"conv-{str(uuid.uuid4())[:8]}"
            print(f"{Fore.CYAN}Generated new conversation ID: {self.conversation_id}{Style.RESET_ALL}")
        
        # Extract query essence for caching and object ID
        query_essence = self._get_query_essence(query)
        
        # Generate a deterministic object ID based on the query essence if not provided
        if not object_id:
            # Create a stable ID based on query essence, data source and prompt
            # This helps with caching similar queries
            object_id = self._generate_stable_id(query_essence, data_source_id, prompt_id)
        
        # Determine attributes to retrieve based on query type
        attributes_to_retrieve = self._determine_attributes(query)
        
        # Build request data
        data = {
            "query": query,
            "dataSourceID": data_source_id,
            "promptID": prompt_id,
            "save": True,        # Always save responses for caching
            "useCache": False if self.conversation_id else True,  # Don't use cache in conversation mode
            "objectID": object_id,  # Use stable object ID for better caching
            "conversationID": self.conversation_id  # Always include our conversation ID
        }
        
        # Add attributes to retrieve if available
        if attributes_to_retrieve:
            data["attributesToRetrieve"] = attributes_to_retrieve
            if self.debug:
                print(f"{Fore.CYAN}Using attributesToRetrieve: {attributes_to_retrieve}{Style.RESET_ALL}")
                
        # Special handling for food pairing queries
        if self._is_food_pairing_query(query):
            # Extract food items
            food_items = self._extract_food_items(query)
            if food_items:
                # If we have specific food items, use them to find matching objects
                # This helps generate targeted responses about specific foods
                if self.debug:
                    print(f"{Fore.CYAN}Using food items as filter: {food_items}{Style.RESET_ALL}")
                
                # Add additional filters for food items
                food_filter = " OR ".join([f"_tags:{item}" for item in food_items if item.strip()])
                if food_filter:  # Only add the filter if it's not empty
                    if "additionalFilters" in data:
                        data["additionalFilters"] += f" AND ({food_filter})"
                    else:
                        data["additionalFilters"] = food_filter
        
        max_retries = 3
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                print(f"{Fore.CYAN}Sending request to generate response with objectID: {object_id}{Style.RESET_ALL}")
                response = requests.post(endpoint, headers=self.headers, json=data)
                response.raise_for_status()
                
                # Check if we got a cached response
                cached = False
                if 'x-algolia-cached' in response.headers:
                    cached = response.headers['x-algolia-cached'] == 'true'
                    if cached:
                        print(f"{Fore.GREEN}Retrieved cached response from Algolia{Style.RESET_ALL}")
                
                # Parse the response
                response_data = response.json()
                
                # Always make sure the conversation ID is in the response data
                # This ensures we maintain our own conversation ID regardless of what Algolia returns
                response_data["conversationID"] = self.conversation_id
                
                # Verify response was stored by trying to retrieve it immediately
                if not cached and not self.conversation_id:  # Skip verification for conversation mode
                    try:
                        time.sleep(1)  # Brief delay to allow indexing
                        verification = self.client.init_index("algolia_rag_responses").get_object(object_id)
                        print(f"{Fore.GREEN}Successfully verified response storage with ID: {object_id}{Style.RESET_ALL}")
                    except Exception as e:
                        print(f"{Fore.RED}Warning: Response may not have been stored: {e}{Style.RESET_ALL}")
                        # Don't try to manually store for conversation mode
                
                # After receiving the response - fix the prompt ID mismatch
                if not cached and "response" in response_data:
                    try:
                        # Create a copy of the result with our original prompt ID
                        corrected_object = {
                            "objectID": object_id,  # Use our original stable ID
                            "query": query,
                            "response": response_data.get("response", ""),
                            "dataSourceID": data_source_id,
                            "promptID": prompt_id,  # Use our original prompt ID
                            "conversationID": self.conversation_id,
                            "createdAt": datetime.now().isoformat()
                        }
                        
                        # Save the corrected object explicitly
                        print(f"{Fore.CYAN}Saving corrected object with ID {object_id} and consistent prompt ID{Style.RESET_ALL}")
                        self.client.init_index("algolia_rag_responses").save_object(corrected_object)
                    except Exception as save_error:
                        print(f"{Fore.RED}Error saving corrected response: {save_error}{Style.RESET_ALL}")
                
                return response_data
            except requests.exceptions.RequestException as e:
                # Log the error
                self.log_error(
                    error_type="API Error",
                    details=f"Attempt {attempt+1}: {str(e)}"
                )
                
                if hasattr(e, 'response') and hasattr(e.response, 'status_code') and e.response.status_code == 429:  # Rate limit
                    print(f"Rate limit exceeded. Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue
                else:
                    print(f"Error generating response: {e}")
                    if hasattr(e, 'response') and hasattr(e.response, 'text'):
                        print(f"Response: {e.response.text}")
                    # Return a basic response with our conversation ID
                    return {
                        "response": "I encountered an error while processing your request. Please try again.",
                        "conversationID": self.conversation_id
                    }
            except Exception as e:
                # Log the error
                self.log_error(
                    error_type="General Error",
                    details=f"Attempt {attempt+1}: {str(e)}"
                )
                
                print(f"Error: {e}")
                time.sleep(retry_delay)
                retry_delay *= 2
                continue
        
        print(f"Failed to generate response after {max_retries} attempts")
        # Even when all attempts fail, return a response with our conversation ID
        return {
            "response": "I apologize, but I couldn't generate a response after multiple attempts. Please try again later.",
            "conversationID": self.conversation_id
        }
        
    def _generate_stable_id(self, query_essence, data_source_id, prompt_id):
        """Generate a stable ID for caching similar queries"""
        import hashlib

        # Include conversation ID in componenets if available
        conv_component = f"|conv_{self.conversation_id}" if self.conversation_id else ""
        
        # Create a composite string from the key components
        components = f"{query_essence}|{data_source_id}|{prompt_id}{conv_component}"
        
        # Generate a hash
        hash_object = hashlib.md5(components.encode())
        hash_string = hash_object.hexdigest()
        
        # Return a formatted ID
        stable_id = f"sommelier_{hash_string}"
        
        if self.debug:
            print(f"{Fore.CYAN}Generated stable ID: {stable_id} for essence: {query_essence}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}Based on: query='{query_essence}', dataSource='{data_source_id}', prompt='{prompt_id}', converation='{self.conversation_id}'{Style.RESET_ALL}")
        
        return stable_id
        
    def _get_query_essence(self, query):
        """Extract the essence of a query for caching purposes with improved specificity"""
        # Normalize and clean the query
        normalized = query.lower().strip()
        
        # Store the exact query essence for highly precise cache hits
        # Remove some very common words but keep most of the query intact for better exact matching
        exact_words = normalized.split()
        exact_stopwords = {"a", "an", "the", "is", "are", "that", "this", "with", "for", "to", "in", "of", "and", "or"}
        exact_query = " ".join([word for word in exact_words if word not in exact_stopwords])
        
        # Hash the exact query if it's long (over 30 chars)
        if len(exact_query) > 30:
            import hashlib
            exact_hash = hashlib.md5(exact_query.encode()).hexdigest()[:10]
            exact_query = f"q_{exact_hash}"
        
        # Special handling for food pairing queries
        if self._is_food_pairing_query(normalized):
            food_items = self._extract_food_items(normalized)
            if food_items:
                # Include the exact query for higher precision
                return f"exact_{exact_query}_pair_with_{' '.join(food_items)}"
        
        # For recommendation queries
        if any(term in normalized for term in ["recommend", "suggest", "looking for", "what wine"]):
            # Extract specific constraints like price, color, region
            wine_type = self._extract_wine_type(normalized)
            price_range = self._extract_price_range(normalized)
            region = self._extract_region(normalized)
            
            constraints = []
            if wine_type:
                constraints.append(wine_type)
            if price_range:
                constraints.append(price_range)
            if region:
                constraints.append(region)
                
            if constraints:
                # Create a more specific essence for recommendation queries
                return f"exact_{exact_query}_recommend_{' '.join(constraints)}"
        
        # For all other queries, use a combination of exact query and key terms
        key_terms = self._extract_key_terms(normalized)
        
        # Include the exact query hash at the start for higher precision
        return f"exact_{exact_query}_{key_terms}"
        
    def _is_food_pairing_query(self, query):
        """Check if this is a food pairing query with improved validation"""
        # Clean the query first
        query = query.lower().strip()
        
        # Remove any conversation artifacts
        suspicious_tokens = ["assistant:", "user:", "assistant", "user", "sommelier:"]
        for token in suspicious_tokens:
            if token in query:
                query = query.replace(token, "")
        
        pairing_terms = ["pair", "pairing", "goes with", "good with", "match", "matching", "complement"]
        
        # Check if any pairing term is in the query
        is_pairing = any(term in query for term in pairing_terms)
        
        # For follow-up questions, be more strict - require both a pairing term and a food term
        if "that" in query or "this" in query:
            food_related = any(term in query for term in ["food", "dish", "meal", "restaurant", "cuisine"])
            return is_pairing and food_related
        
        return is_pairing
        
    def _determine_attributes(self, query):
        """Determine which attributes to retrieve based on query type"""
        normalized = query.lower()
        
        # Default attributes for all queries
        attributes = ["name", "winery_name", "year", "country_name", "region_name", "type_name", "grape_names"]
        
        # Add specialized attributes based on query type
        if "pair" in normalized or "food" in normalized:
            attributes.extend(["ai_food_pairings", "ai_taste_profile"])
        
        if "taste" in normalized or "flavor" in normalized:
            attributes.extend(["ai_taste_profile", "ai_primary_tastes", "ai_secondary_tastes", "ai_tertiary_tastes"])
            
        if "quality" in normalized or "rating" in normalized:
            attributes.extend(["average_rating", "ai_quality_score", "ai_quality_assessment"])
            
        if "price" in normalized or "value" in normalized or "cost" in normalized:
            attributes.extend(["price", "price_range", "ai_price_tier", "ai_value_rating"])
            
        return attributes
    
    def _extract_wine_type(self, query):
        """Extract wine type from query"""
        wine_types = {
            "red": ["red", "cabernet", "merlot", "pinot noir", "syrah", "shiraz", "malbec", "zinfandel"],
            "white": ["white", "chardonnay", "sauvignon blanc", "pinot grigio", "riesling", "moscato"],
            "sparkling": ["sparkling", "champagne", "prosecco", "cava", "bubbly"],
            "rose": ["rosé", "rose", "pink wine"]
        }
        
        for wine_type, terms in wine_types.items():
            if any(term in query for term in terms):
                return wine_type
        
        return None
    
    def _infer_prompt_type_from_query(self, query):
        """Infer the prompt type based on the query and conversation history"""
        query_lower = query.lower()
        
        # If the conversation history is empty, return None for automatic detection
        if not self.conversation_history:
            return None
        
        # Look at the current query for clues
        
        # Check for food pairing indicators in follow-up questions
        if any(term in query_lower for term in ["pair", "go with", "serve with", "dish", "meal", "food"]):
            if "food_pairing" in self.prompts:
                return "food_pairing"
        
        # Check for wine recommendation indicators in follow-up questions
        if any(term in query_lower for term in ["recommend", "suggest", "alternative", "similar", "prefer"]):
            if "recommendations" in self.prompts:
                return "recommendations"
                
        # Check for tasting indicators in follow-up questions
        if any(term in query_lower for term in ["taste", "flavor", "aroma", "smell", "drink", "palate"]):
            if "tasting" in self.prompts:
                return "tasting"
        
        # If we can't determine from current query, check previous assistant response
        if len(self.conversation_history) >= 2:
            last_assistant_msg = None
            
            # Find the last assistant message
            for msg in reversed(self.conversation_history):
                if msg["role"] == "assistant":
                    last_assistant_msg = msg["content"].lower()
                    break
            
            # If found, analyze it for context
            if last_assistant_msg:
                # Check if last response was about wine recommendations
                if any(term in last_assistant_msg for term in ["recommend", "suggest", "try this", "excellent choice"]):
                    if "recommendations" in self.prompts:
                        return "recommendations"
                
                # Check if it was about food pairings
                if any(term in last_assistant_msg for term in ["pair", "complement", "go well with", "match"]):
                    if "food_pairing" in self.prompts:
                        return "food_pairing"
                        
                # Check if it was about tasting notes
                if any(term in last_assistant_msg for term in ["taste", "flavor", "palate", "aroma", "bouquet"]):
                    if "tasting" in self.prompts:
                        return "tasting"
        
        # Default to None (auto-select) if we can't determine
        return None
    
    def _extract_price_range(self, query):
        """Extract price range from query"""
        import re
        
        # Look for dollar amounts like $20, $30-50, under $30
        price_patterns = [
            r'under\s+\$(\d+)',
            r'less than\s+\$(\d+)',
            r'around\s+\$(\d+)',
            r'\$(\d+)-\$?(\d+)',
            r'\$(\d+)',
            r'(\d+)\s+dollars'
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, query)
            if match:
                if len(match.groups()) == 1:
                    return f"price_{match.group(1)}"
                elif len(match.groups()) == 2:
                    return f"price_{match.group(1)}_to_{match.group(2)}"
        
        # Look for price descriptors
        if "cheap" in query or "inexpensive" in query or "budget" in query:
            return "price_budget"
        elif "expensive" in query or "premium" in query or "luxury" in query:
            return "price_premium"
        
        return None

    def _extract_region(self, query):
        """Extract wine region from query"""
        # Common wine regions
        regions = {
            "france": ["french", "france", "bordeaux", "burgundy", "champagne", "rhone", "loire"],
            "italy": ["italian", "italy", "tuscany", "piedmont", "veneto", "sicily"],
            "spain": ["spanish", "spain", "rioja", "catalonia", "ribera"],
            "usa": ["american", "california", "napa", "sonoma", "oregon", "washington"],
            "australia": ["australian", "australia", "barossa", "margaret river"],
            "new_zealand": ["new zealand", "marlborough"],
            "argentina": ["argentinian", "argentina", "mendoza"],
            "chile": ["chilean", "chile"],
            "germany": ["german", "germany", "mosel", "rheingau"]
        }
        
        for region, terms in regions.items():
            if any(term in query.lower() for term in terms):
                return region
        
        return None

    def clear_conversation(self):
        """Clear the conversation history"""
        self.conversation_history = []
        self.conversation_id = None
        return "Conversation history cleared. Let's start fresh!"


class SommelierCLI(cmd.Cmd):
    """Command-line interface for the Sommelier Assistant with metrics commands"""
    
    intro = f"""
    {Fore.MAGENTA}🍷 Welcome to the Sommelier AI Assistant! 🍷{Style.RESET_ALL}
    
    I'm your personal sommelier, here to help with wine recommendations,
    food pairings, and wine education.
    
    {Fore.CYAN}Type 'help' for a list of commands or just start asking questions about wine!{Style.RESET_ALL}
    
    Example queries:
    - What wine would pair well with steak?
    - Tell me about Cabernet Sauvignon grape
    - Recommend a good white wine under $30
    - Explain primary, secondary, and tertiary tastes
    - What's the soil like in Bordeaux vineyards?
    
    Type 'quit' or 'exit' to exit the program.
    """
    
    prompt = f"\n{Fore.RED}🍷 Ask Sommelier: {Style.RESET_ALL}"
    
    def __init__(self, sommelier):
        super().__init__()
        self.sommelier = sommelier
        self.terminal_width = os.get_terminal_size().columns
        self.use_streaming = False  # Disable streaming by default - more reliable
    
    def default(self, line):
        """Handle user queries"""
        if line.lower() in ['quit', 'exit', 'bye']:
            return self.do_quit(line)
        
        # Process the query
        print(f"\n{Fore.YELLOW}Thinking...{Style.RESET_ALL}")
        
        # For now, use non-streaming mode which is more reliable
        response = self.sommelier.process_query(line, stream=False)
        
        # Format and print the response with word wrapping
        print(f"\n{Fore.GREEN}Sommelier: {Style.RESET_ALL}")
        
        # Avoid word wrapping for Markdown content - breaks formatting
        if "```" in response or "**" in response:
            # Just apply minimal indentation for consistency
            formatted_response = "\n  ".join(response.split("\n"))
            print("  " + formatted_response)
        else:
            # Use word wrapping for plain text responses
            wrapped_response = textwrap.fill(response, 
                                         width=self.terminal_width-2, 
                                         replace_whitespace=False, 
                                         break_on_hyphens=False)
            print(wrapped_response)
    
    def do_toggle_stream(self, arg):
        """Toggle streaming mode on/off (currently disabled due to API issues)"""
        # Keep streaming disabled - it's unreliable with current API
        self.use_streaming = False
        print(f"\n{Fore.CYAN}Streaming mode is currently disabled for reliability.{Style.RESET_ALL}")
        print(f"{Fore.CYAN}The sommelier will provide complete responses using non-streaming mode.{Style.RESET_ALL}")
    
    def do_clear(self, arg):
        """Clear the conversation history"""
        response = self.sommelier.clear_conversation()
        print(f"\n{Fore.GREEN}Sommelier: {Style.RESET_ALL}{response}")
    
    def do_recommend(self, arg):
        """Get wine recommendations"""
        if not arg:
            arg = "Can you recommend some wines for me?"
        
        print(f"\n{Fore.YELLOW}Thinking about recommendations...{Style.RESET_ALL}")
        
        if self.use_streaming:
            self.sommelier.process_query(arg, prompt_type="recommendations", stream=True)
        else:
            response = self.sommelier.process_query(arg, prompt_type="recommendations")
            print(f"\n{Fore.GREEN}Sommelier: {Style.RESET_ALL}")
            wrapped_response = textwrap.fill(response, 
                                         width=self.terminal_width-2, 
                                         replace_whitespace=False, 
                                         break_on_hyphens=False)
            print(wrapped_response)
    
    def do_pair(self, arg):
        """Get food and wine pairings"""
        if not arg:
            arg = "What food pairs well with wine?"
            
        print(f"\n{Fore.YELLOW}Thinking about pairings...{Style.RESET_ALL}")
        
        if self.use_streaming:
            self.sommelier.process_query(arg, prompt_type="food_pairing", stream=True)
        else:
            response = self.sommelier.process_query(arg, prompt_type="food_pairing")
            print(f"\n{Fore.GREEN}Sommelier: {Style.RESET_ALL}")
            wrapped_response = textwrap.fill(response, 
                                         width=self.terminal_width-2, 
                                         replace_whitespace=False, 
                                         break_on_hyphens=False)
            print(wrapped_response)
    
    def do_explain(self, arg):
        """Get explanations about wine terms and concepts"""
        if not arg:
            arg = "Can you explain wine tasting?"
            
        print(f"\n{Fore.YELLOW}Preparing explanation...{Style.RESET_ALL}")
        
        if self.use_streaming:
            self.sommelier.process_query(arg, prompt_type="education", stream=True)
        else:
            response = self.sommelier.process_query(arg, prompt_type="education")
            print(f"\n{Fore.GREEN}Sommelier: {Style.RESET_ALL}")
            wrapped_response = textwrap.fill(response, 
                                         width=self.terminal_width-2, 
                                         replace_whitespace=False, 
                                         break_on_hyphens=False)
            print(wrapped_response)
    
    def do_winery(self, arg):
        """Get information about wineries and vineyards"""
        if not arg:
            arg = "Tell me about some notable wineries"
            
        print(f"\n{Fore.YELLOW}Researching wineries...{Style.RESET_ALL}")
        
        if self.use_streaming:
            self.sommelier.process_query(arg, prompt_type="vineyard_info", stream=True)
        else:
            response = self.sommelier.process_query(arg, prompt_type="vineyard_info")
            print(f"\n{Fore.GREEN}Sommelier: {Style.RESET_ALL}")
            wrapped_response = textwrap.fill(response, 
                                         width=self.terminal_width-2, 
                                         replace_whitespace=False, 
                                         break_on_hyphens=False)
            print(wrapped_response)
    
    def do_taste(self, arg):
        """Get wine tasting guidance"""
        if not arg:
            arg = "How should I taste and evaluate wine?"
            
        print(f"\n{Fore.YELLOW}Preparing tasting notes...{Style.RESET_ALL}")
        
        if self.use_streaming:
            self.sommelier.process_query(arg, prompt_type="tasting", stream=True)
        else:
            response = self.sommelier.process_query(arg, prompt_type="tasting")
            print(f"\n{Fore.GREEN}Sommelier: {Style.RESET_ALL}")
            wrapped_response = textwrap.fill(response, 
                                         width=self.terminal_width-2, 
                                         replace_whitespace=False, 
                                         break_on_hyphens=False)
            print(wrapped_response)
    
    def do_metrics(self, arg):
        """Show metrics dashboard"""
        self.sommelier.print_metrics_summary()
    
    def do_save_metrics(self, arg):
        """Save metrics to file"""
        self.sommelier.save_metrics()
    
    def do_charts(self, arg):
        """Generate metrics charts"""
        output_dir = arg.strip() if arg.strip() else "./metrics_charts"
        self.sommelier.generate_charts(output_dir)
    
    def do_report(self, arg):
        """Export detailed metrics report"""
        output_file = arg.strip() if arg.strip() else "sommelier_metrics_report.txt"
        self.sommelier.export_detailed_report(output_file)
    
    def do_reset_metrics(self, arg):
        """Reset metrics for a new session"""
        self.sommelier.reset_metrics()
        print(f"{Fore.GREEN}Metrics reset for a new session{Style.RESET_ALL}")
    
    def do_quit(self, arg):
        """Exit the program"""
        print(f"\n{Fore.MAGENTA}Thank you for using the Sommelier AI Assistant. Cheers! 🍷{Style.RESET_ALL}")
        return True
    
    def do_help(self, arg):
        """Show help menu"""
        if arg == "metrics":
            print(f"\n{Fore.CYAN}Metrics Commands:{Style.RESET_ALL}")
            print(f"  {Fore.YELLOW}metrics{Style.RESET_ALL} - Show metrics dashboard")
            print(f"  {Fore.YELLOW}save_metrics{Style.RESET_ALL} - Save metrics to file")
            print(f"  {Fore.YELLOW}reset_metrics{Style.RESET_ALL} - Reset metrics for a new session")
            print(f"  {Fore.YELLOW}charts [output_dir]{Style.RESET_ALL} - Generate metrics charts")
            print(f"  {Fore.YELLOW}report [output_file]{Style.RESET_ALL} - Export detailed metrics report")
            return
            
        # Original help commands
        print(f"\n{Fore.CYAN}Sommelier AI Assistant Commands:{Style.RESET_ALL}")
        print(f"  {Fore.YELLOW}recommend [query]{Style.RESET_ALL} - Get wine recommendations")
        print(f"  {Fore.YELLOW}pair [food]{Style.RESET_ALL} - Get wine pairings for food")
        print(f"  {Fore.YELLOW}explain [topic]{Style.RESET_ALL} - Learn about wine concepts")
        print(f"  {Fore.YELLOW}winery [name]{Style.RESET_ALL} - Get information about wineries")
        print(f"  {Fore.YELLOW}taste [wine]{Style.RESET_ALL} - Get wine tasting guidance")
        print(f"  {Fore.YELLOW}clear{Style.RESET_ALL} - Clear conversation history")
        print(f"  {Fore.YELLOW}quit{Style.RESET_ALL} - Exit the program")
        
        # Add metrics commands
        print(f"\n{Fore.CYAN}Metrics Commands:{Style.RESET_ALL}")
        print(f"  {Fore.YELLOW}metrics{Style.RESET_ALL} - Show metrics dashboard")
        print(f"  {Fore.YELLOW}save_metrics{Style.RESET_ALL} - Save metrics to file")
        print(f"  {Fore.YELLOW}reset_metrics{Style.RESET_ALL} - Reset metrics for a new session")
        print(f"  {Fore.YELLOW}charts [output_dir]{Style.RESET_ALL} - Generate metrics charts")
        print(f"  {Fore.YELLOW}report [output_file]{Style.RESET_ALL} - Export detailed metrics report")
        
        print(f"\nYou can also simply type your questions directly.")
    
    # Aliases
    do_exit = do_quit
    do_bye = do_quit
    do_stream = do_toggle_stream


def main():
    """Main function to run the Sommelier Assistant"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Run the Sommelier AI Assistant')
    
    parser.add_argument('--app-id', required=True,
                        help='Algolia Application ID')
    parser.add_argument('--api-key', required=True,
                        help='Algolia API Key')
    parser.add_argument('--index', required=True,
                        help='Algolia Index Name containing wine data')
    parser.add_argument('--region', default="us", choices=['us', 'eu'],
                        help='Algolia GenAI Toolkit region (default: us)')
    parser.add_argument('--metrics-file', default="sommelier_metrics.json",
                        help='Path to metrics file (default: sommelier_metrics.json)')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug mode with verbose output')
    
    args = parser.parse_args()
    
    try:
        # Initialize the Sommelier Assistant with integrated metrics
        sommelier = SommelierAssistant(
            app_id=args.app_id,
            api_key=args.api_key,
            index_name=args.index,
            region=args.region,
            debug=args.debug,
            metrics_file=args.metrics_file
        )
        
        # Start the CLI
        cli = SommelierCLI(sommelier)
        cli.cmdloop()
        
        # Save metrics before exiting
        sommelier.save_metrics()
    except KeyboardInterrupt:
        print(f"\n{Fore.MAGENTA}Thank you for using the Sommelier AI Assistant. Cheers! 🍷{Style.RESET_ALL}")
        # Try to save metrics before exiting
        try:
            if 'sommelier' in locals() and hasattr(sommelier, 'save_metrics'):
                sommelier.save_metrics()
        except:
            pass
    except Exception as e:
        print(f"\n{Fore.RED}Error: {e}{Style.RESET_ALL}")
        print("If this is a dependency issue, please install required packages:")
        print("pip install algoliasearch colorama requests matplotlib numpy")


if __name__ == "__main__":
    main()