// src/services/api.js
import axios from 'axios';

// Updated API URL - note we're now directly accessing the Flask routes
// without the /api prefix if your routes don't include it
const API_URL = 'http://localhost:5001';

// Create axios instance
const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// API service functions
const sommelierService = {
  // Test the API connection
  testConnection: async () => {
    try {
      const response = await api.get('/test');
      console.log("API test response:", response.data);
      return response.data;
    } catch (error) {
      console.error('API connection test failed:', error);
      throw error;
    }
  },
  
  // Send a query to the sommelier assistant
  sendQuery: async (query, promptType = null) => {
    try {
      console.log(`Sending query to API: ${query} (promptType: ${promptType || 'auto'})`);
      const response = await api.post('/api/query', { 
        query, 
        promptType 
      });
      console.log('Query response:', response.data);
      return response.data;
    } catch (error) {
      console.error('Error sending query:', error);
      console.error('Error details:', error.response ? error.response.data : 'No response data');
      throw error;
    }
  },
  
  // Get metrics data
  getMetrics: async () => {
    try {
      const response = await api.get('/api/metrics');
      return response.data;
    } catch (error) {
      console.error('Error fetching metrics:', error);
      throw error;
    }
  },
  
  // Get available prompt types
  getPromptTypes: async () => {
    try {
      const response = await api.get('/api/prompt-types');
      return response.data.prompt_types;
    } catch (error) {
      console.error('Error fetching prompt types:', error);
      throw error;
    }
  },
  
  // Clear conversation history
  clearConversation: async () => {
    try {
      const response = await api.post('/api/clear-conversation');
      return response.data;
    } catch (error) {
      console.error('Error clearing conversation:', error);
      throw error;
    }
  },
  
  // Reset metrics
  resetMetrics: async () => {
    try {
      const response = await api.post('/api/reset-metrics');
      return response.data;
    } catch (error) {
      console.error('Error resetting metrics:', error);
      throw error;
    }
  }
};

export default sommelierService;