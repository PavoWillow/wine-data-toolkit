// src/pages/Dashboard.jsx - Updated with automatic metrics refresh
import { useState, useEffect, useRef } from 'react';
import sommelierService from '../services/api';
import ChatPanel from '../components/ChatPanel';
import MetricsPanel from '../components/MetricsPanel';

function Dashboard({ metrics: initialMetrics, promptTypes }) {
  const [conversations, setConversations] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [selectedPromptType, setSelectedPromptType] = useState(null);
  const [currentMetrics, setCurrentMetrics] = useState(initialMetrics);
  
  // Set up automatic metrics refresh
  useEffect(() => {
    // Function to fetch latest metrics
    const fetchMetrics = async () => {
      try {
        const updatedMetrics = await sommelierService.getMetrics();
        setCurrentMetrics(updatedMetrics);
      } catch (error) {
        console.error("Error refreshing metrics:", error);
      }
    };
    
    // Set up interval for periodic refresh (every 3 seconds)
    const refreshInterval = setInterval(fetchMetrics, 3000);
    
    // Clean up on component unmount
    return () => clearInterval(refreshInterval);
  }, []);
  
  // Refresh metrics after a new query is processed
  const refreshMetricsAfterQuery = async () => {
    try {
      const updatedMetrics = await sommelierService.getMetrics();
      setCurrentMetrics(updatedMetrics);
    } catch (error) {
      console.error("Error refreshing metrics after query:", error);
    }
  };
  
  const handleSendQuery = async (query) => {
    if (!query.trim() || isProcessing) return;
    
    // Add user message to conversation
    setConversations(prev => [...prev, { 
      role: 'user', 
      content: query,
      timestamp: new Date().toISOString()
    }]);
    
    setIsProcessing(true);
    
    try {
      // Show typing indicator
      setConversations(prev => [...prev, { 
        role: 'assistant', 
        content: '...',
        isTyping: true,
        timestamp: new Date().toISOString()
      }]);
      
      // Send query to API
      const response = await sommelierService.sendQuery(query, selectedPromptType);
      
      // Remove typing indicator and add actual response
      setConversations(prev => {
        const filtered = prev.filter(msg => !msg.isTyping);
        return [...filtered, { 
          role: 'assistant', 
          content: response.response,
          isCacheHit: response.cache_hit,
          responseTime: response.response_time,
          queryType: response.query_type,
          timestamp: new Date().toISOString()
        }];
      });
      
      // Refresh metrics after processing the query
      await refreshMetricsAfterQuery();
      
    } catch (error) {
      console.error("Error sending query:", error);
      
      // Remove typing indicator and add error message
      setConversations(prev => {
        const filtered = prev.filter(msg => !msg.isTyping);
        return [...filtered, { 
          role: 'assistant', 
          content: 'Sorry, I encountered an error while processing your request. Please try again.',
          isError: true,
          timestamp: new Date().toISOString()
        }];
      });
    } finally {
      setIsProcessing(false);
    }
  };
  
  const clearConversation = async () => {
    try {
      await sommelierService.clearConversation();
      setConversations([]);
    } catch (error) {
      console.error("Error clearing conversation:", error);
    }
  };
  
  return (
    <div className="dashboard-container">
      <div className="dashboard-chat">
        <ChatPanel 
          conversations={conversations} 
          onSendQuery={handleSendQuery}
          onClearConversation={clearConversation}
          promptTypes={promptTypes}
          selectedPromptType={selectedPromptType}
          onChangePromptType={setSelectedPromptType}
          isProcessing={isProcessing}
        />
      </div>
      <div className="dashboard-metrics">
        <MetricsPanel metrics={currentMetrics} />
      </div>
    </div>
  );
}

export default Dashboard;