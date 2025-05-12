// src/App.jsx - Updated to include API Test
import React from 'react'
import { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import sommelierService from './services/api';
import Dashboard from './pages/Dashboard';
import './App.css';

function App() {
  const [metrics, setMetrics] = useState(null);
  const [promptTypes, setPromptTypes] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [apiStatus, setApiStatus] = useState('testing'); // 'testing', 'connected', 'failed'
  
  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        setIsLoading(true);
        
        // Test API connection first
        try {
          await sommelierService.testConnection();
          setApiStatus('connected');
          
          // Now try to fetch real data
          try {
            const types = await sommelierService.getPromptTypes();
            setPromptTypes(types);
            
            const metricsData = await sommelierService.getMetrics();
            setMetrics(metricsData);
          } catch (dataError) {
            console.error("Error fetching data:", dataError);
            // Use mock data if API data fetch fails
            console.log('Using mock data');
            setPromptTypes(['sommelier', 'recommendations', 'food_pairing', 'education', 'vineyard_info', 'tasting']);
            setMetrics({
              total_queries: 12,
              cache_hits: 8,
              cache_misses: 4,
              hit_rate: 66.67,
              avg_cache_hit_time: 0.43,
              avg_generation_time: 4.15,
              estimated_cost_saved: 0.0160,
              query_type_performance: [
                { type: 'food_pairing', total: 5, hits: 4, misses: 1, hit_rate: 80 },
                { type: 'recommendations', total: 4, hits: 2, misses: 2, hit_rate: 50 },
                { type: 'sommelier', total: 3, hits: 2, misses: 1, hit_rate: 66.67 }
              ]
            });
          }
        } catch (connectionError) {
          console.error("API connection failed:", connectionError);
          setApiStatus('failed');
          
          // Set mock data anyway so UI still works
          setPromptTypes(['sommelier', 'recommendations', 'food_pairing', 'education', 'vineyard_info', 'tasting']);
          setMetrics({
            total_queries: 12,
            cache_hits: 8,
            cache_misses: 4,
            hit_rate: 66.67,
            avg_cache_hit_time: 0.43,
            avg_generation_time: 4.15,
            estimated_cost_saved: 0.0160,
            query_type_performance: [
              { type: 'food_pairing', total: 5, hits: 4, misses: 1, hit_rate: 80 },
              { type: 'recommendations', total: 4, hits: 2, misses: 2, hit_rate: 50 },
              { type: 'sommelier', total: 3, hits: 2, misses: 1, hit_rate: 66.67 }
            ]
          });
        }
      } catch (error) {
        console.error("Error in initial data fetch:", error);
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchInitialData();
  }, []);
  
  return (
    <Router>
      <div className="app-container">
        <nav className="navbar">
          <div className="navbar-container">
            <div className="navbar-logo">
              <h1>Sommelier AI</h1>
            </div>
            <div className="navbar-links">
              <Link to="/" className="nav-link">Dashboard</Link>
              <Link to="/analytics" className="nav-link">Analytics</Link>
              <Link to="/about" className="nav-link">About</Link>
            </div>
          </div>
        </nav>
        
        <main className="main-content">
          {isLoading ? (
            <div className="loading">Loading...</div>
          ) : (
            <>
              
              <Routes>
                <Route 
                  path="/" 
                  element={<Dashboard metrics={metrics} promptTypes={promptTypes} />} 
                />
                <Route 
                  path="/analytics" 
                  element={<div>Analytics Page Coming Soon</div>} 
                />
                <Route 
                  path="/about" 
                  element={<div>About Page Coming Soon</div>} 
                />
              </Routes>
            </>
          )}
        </main>
        
        <footer className="footer">
          <div className="footer-container">
            <div className="footer-copyright">
              &copy; {new Date().getFullYear()} Sommelier AI Assistant. All rights reserved.
            </div>
            <div className="footer-powered-by">
              Powered by Algolia
            </div>
          </div>
        </footer>
      </div>
    </Router>
  );
}

export default App;