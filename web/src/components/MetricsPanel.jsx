// src/components/MetricsPanel.jsx
import { useEffect, useRef } from 'react';
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js';
import { Doughnut } from 'react-chartjs-2';

// Register Chart.js components
ChartJS.register(ArcElement, Tooltip, Legend);

function MetricsPanel({ metrics }) {
  // Create ref for charts
  const chartRef = useRef(null);
  
  if (!metrics) {
    return (
      <div className="metrics-panel">
        <div className="metrics-header">
          <h2>Cache Analytics</h2>
        </div>
        <div className="metrics-content">
          <div className="loading">Loading metrics...</div>
        </div>
      </div>
    );
  }
  
  const formatTime = (seconds) => {
    if (seconds < 0.1) {
      return `${(seconds * 1000).toFixed(0)}ms`;
    }
    return `${seconds.toFixed(2)}s`;
  };
  
  // Data for cache hit/miss chart
  const cacheData = {
    labels: ['Cache Hits', 'Cache Misses'],
    datasets: [
      {
        data: [metrics.cache_hits, metrics.cache_misses],
        backgroundColor: ['#4CAF50', '#F44336'],
        borderColor: ['#388E3C', '#D32F2F'],
        borderWidth: 1,
      },
    ],
  };
  
  // Options for cache hit/miss chart
  const cacheOptions = {
    plugins: {
      legend: {
        position: 'bottom',
      },
    },
    cutout: '70%',
    responsive: true,
    maintainAspectRatio: false,
  };
  
  // Calculate speedup factor
  const speedupFactor = metrics.avg_generation_time && metrics.avg_cache_hit_time 
    ? (metrics.avg_generation_time / metrics.avg_cache_hit_time).toFixed(1)
    : 'N/A';
  
  return (
    <div className="metrics-panel">
      <div className="metrics-header">
        <h2>Cache Analytics</h2>
      </div>
      
      <div className="metrics-content">
        <div className="metrics-grid">
          <div className="metric-card">
            <div className="metric-label">Total Queries</div>
            <div className="metric-value">{metrics.total_queries}</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Cache Hit Rate</div>
            <div className="metric-value green">{metrics.hit_rate}%</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Cache Hits</div>
            <div className="metric-value">{metrics.cache_hits}</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Cache Misses</div>
            <div className="metric-value">{metrics.cache_misses}</div>
          </div>
        </div>
        
        <div className="metrics-section">
          <h3>📊 Cache Performance</h3>
          <div className="chart-container">
            <Doughnut data={cacheData} options={cacheOptions} ref={chartRef} />
          </div>
        </div>
        
        <div className="metrics-section">
          <h3>⏱️ Response Times</h3>
          <div className="metrics-row">
            <span className="metrics-label">Cache Hit:</span>
            <span className="metrics-value">{formatTime(metrics.avg_cache_hit_time || 0)}</span>
          </div>
          <div className="metrics-row">
            <span className="metrics-label">Generation:</span>
            <span className="metrics-value">{formatTime(metrics.avg_generation_time || 0)}</span>
          </div>
          <div className="metrics-row">
            <span className="metrics-label">Speedup Factor:</span>
            <span className="metrics-value">{speedupFactor}x</span>
          </div>
        </div>
        
        <div className="metrics-section">
          <h3>💰 Cost Savings</h3>
          <div className="metrics-row">
            <span className="metrics-label">Without Caching:</span>
            <span className="metrics-value">${metrics.potential_cost_without_caching?.toFixed(4)}</span>
          </div>
          <div className="metrics-row">
            <span className="metrics-label">With Caching:</span>
            <span className="metrics-value">${metrics.actual_cost_with_caching?.toFixed(4)}</span>
          </div>
          <div className="metrics-row">
            <span className="metrics-label">Total Saved:</span>
            <span className="metrics-value" style={{ color: 'green' }}>
              ${metrics.estimated_cost_saved?.toFixed(4)}
            </span>
          </div>
        </div>
        
        {metrics.query_type_performance && metrics.query_type_performance.length > 0 && (
          <div className="metrics-section">
            <h3>🔍 Query Types</h3>
            {metrics.query_type_performance.map((type, index) => (
              <div key={index} className="metrics-row">
                <span className="metrics-label">{type.type}:</span>
                <span className="metrics-value">{type.hit_rate}% ({type.hits}/{type.total})</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default MetricsPanel;