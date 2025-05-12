// src/pages/Dashboard.jsx
import { useState, useEffect, useRef } from 'react';
import ChatPanel from '../components/ChatPanel';
import MetricsPanel from '../components/MetricsPanel';
import sommelierService from '../services/api';

function Dashboard({ metrics, promptTypes }) {
  const [conversations, setConversations] = useState([]);
  const [selectedPromptType, setSelectedPromptType] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentMetrics, setCurrentMetrics] = useState(metrics);
  const [conversationID, setConversationID] = useState(null); // Track conversation ID
  
  // Use a ref to track if we're in a conversation
  const isInConversation = useRef(false);
  
  // Debug conversation state
  useEffect(() => {
    if (conversationID) {
      console.log(`Active conversation ID: ${conversationID}`);
      isInConversation.current = true;
      // Store in localStorage for persistence
      localStorage.setItem('sommelierConversationID', conversationID);
    }
  }, [conversationID]);

  // Add initialization to recover conversation ID
  useEffect(() => {
    const savedID = localStorage.getItem('sommelierConversationID');
    if (savedID) {
      setConversationID(savedID);
      isInConversation.current = true;
      console.log(`Recovered conversation ID: ${savedID}`);
    }
  }, []);
  
  // Update metrics periodically
  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const metricsData = await sommelierService.getMetrics();
        setCurrentMetrics(metricsData);
      } catch (error) {
        console.error("Error fetching metrics:", error);
      }
    };
    
    // Initial update
    fetchMetrics();
    
    // Set up interval for updates
    const intervalId = setInterval(fetchMetrics, 3000);
    
    // Clean up interval on component unmount
    return () => clearInterval(intervalId);
  }, []);
  
  // Handle sending a query to the sommelier assistant
  const handleSendQuery = async (query) => {
    try {
      setIsProcessing(true);
      
      // Add user message to the conversation
      setConversations(prev => [...prev, { role: 'user', content: query }]);
      
      // Add "thinking" message
      setConversations(prev => [...prev, { 
        role: 'assistant', 
        isTyping: true, 
        content: 'Thinking...' 
      }]);

      console.log(`Sending query with conversation ID: ${conversationID || 'NEW'}`);
      
      // Send query to API with current conversation ID if available
      const response = await sommelierService.sendQuery(
        query, 
        selectedPromptType,
        conversationID  // Pass conversation ID to maintain context
      );
      
      // Update conversation ID if returned from API
      if (response.conversationID) {
        console.log(`Received conversation ID: ${response.conversationID}`);
        setConversationID(response.conversationID);
        isInConversation.current = true;
      }
      
      // Remove "thinking" message and add real response
      setConversations(prev => [
        ...prev.slice(0, -1), // Remove the "thinking" message
        { 
          role: 'assistant', 
          content: response.response,
          isCacheHit: Boolean(response.cache_hit) || response.response_time < 0.3,
          responseTime: response.response_time,
          queryType: response.query_type
        }
      ]);
      
      // Fetch updated metrics after query
      const metricsData = await sommelierService.getMetrics();
      setCurrentMetrics(metricsData);
    } catch (error) {
      console.error("Error sending query:", error);
      
      // Remove "thinking" message and add error message
      setConversations(prev => [
        ...prev.slice(0, -1), // Remove the "thinking" message
        { 
          role: 'assistant', 
          content: "I'm sorry, I couldn't generate a response. Please try again."
        }
      ]);
    } finally {
      setIsProcessing(false);
    }
  };
  
  // Handle clearing the conversation
  const handleClearConversation = async () => {
    try {
      // Call the API to clear conversation state
      await sommelierService.clearConversation();
      
      // Clear the local state
      setConversations([]);
      setConversationID(null); // Reset conversation ID
      isInConversation.current = false;
      console.log("Conversation cleared - ID reset to null");
      
      // Fetch updated metrics
      const metricsData = await sommelierService.getMetrics();
      setCurrentMetrics(metricsData);
    } catch (error) {
      console.error("Error clearing conversation:", error);
    }
  };
  
  // Handle changing the prompt type
  const handleChangePromptType = (type) => {
    // Changing prompt type should clear conversation if we're in one
    if (isInConversation.current) {
      handleClearConversation();
    }
    
    setSelectedPromptType(type === '' ? null : type);
  };
  
  return (
    <div className="dashboard-container">
      <ChatPanel 
        conversations={conversations}
        onSendQuery={handleSendQuery}
        onClearConversation={handleClearConversation}
        promptTypes={promptTypes}
        selectedPromptType={selectedPromptType}
        onChangePromptType={handleChangePromptType}
        isProcessing={isProcessing}
        isInConversation={isInConversation.current}
      />
      <MetricsPanel metrics={currentMetrics} />
    </div>
  );
}

export default Dashboard;