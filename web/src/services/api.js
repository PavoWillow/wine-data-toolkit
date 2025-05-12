// src/services/api.js
import axios from 'axios';

// API URL for the Flask backend
const API_URL = 'http://localhost:5001';

// Create axios instance
const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Try to get persisted conversation ID from localStorage
const getPersistedConversationID = () => {
  return localStorage.getItem('sommelierConversationID');
};

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
  sendQuery: async (query, promptType = null, conversationID = null) => {
    try {
      // If no conversationID provided but we have one in localStorage, use that
      if (!conversationID) {
        const storedID = getPersistedConversationID();
        if (storedID) {
          console.log(`API Service: Recovered conversation ID from storage: ${storedID}`);
          conversationID = storedID;
        }
      }
      
      console.log(`API Service: Sending query with conversationID: ${conversationID || 'new'}`);
      
      // Build the request object
      const requestData = { 
        query, 
        promptType,
        conversationID  // Always include conversationID (null is fine if not set)
      };
      
      console.log('API Service: Full request data:', JSON.stringify(requestData));
      
      const response = await api.post('/api/query', requestData);
      
      // Log the full response for debugging
      console.log('API Service: Response received:', JSON.stringify(response.data, null, 2));
      
      // Always check for and handle conversationID in the response
      if (response.data && response.data.conversationID) {
        const newConversationID = response.data.conversationID;
        console.log(`API Service: Received conversationID: ${newConversationID}`);
        
        // Store conversation ID in localStorage for persistence
        localStorage.setItem('sommelierConversationID', newConversationID);
      } else {
        console.warn('API Service: No conversationID in response!');
      }
      
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
      console.log('API Service: Clearing conversation history');
      const response = await api.post('/api/clear-conversation');
      
      // Also clear the conversation ID from localStorage
      localStorage.removeItem('sommelierConversationID');
      console.log('API Service: Cleared conversationID from storage');
      
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