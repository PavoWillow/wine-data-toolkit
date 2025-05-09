// src/components/ChatPanel.jsx
import { useState, useRef, useEffect } from 'react';
import CacheHitIndicator from './CacheHitIndicator';

function ChatPanel({ 
  conversations, 
  onSendQuery, 
  onClearConversation,
  promptTypes,
  selectedPromptType,
  onChangePromptType,
  isProcessing
}) {
  const [query, setQuery] = useState('');
  const endOfMessagesRef = useRef(null);
  const textareaRef = useRef(null);
  
  // Scroll to bottom when new messages arrive
  useEffect(() => {
    endOfMessagesRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [conversations]);
  
  // Auto-resize textarea as user types
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${textarea.scrollHeight}px`;
    }
  }, [query]);
  
  const handleSubmit = (e) => {
    e.preventDefault();
    if (query.trim()) {
      onSendQuery(query);
      setQuery('');
    }
  };
  
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };
  
  return (
    <div className="chat-panel">
      <div className="chat-header">
        <h2>Sommelier Assistant</h2>
        <div className="chat-controls">
          <select 
            className="chat-select"
            value={selectedPromptType || ''}
            onChange={(e) => onChangePromptType(e.target.value || null)}
          >
            <option value="">Auto Select</option>
            {promptTypes.map(type => (
              <option key={type} value={type}>{type}</option>
            ))}
          </select>
          <button 
            onClick={onClearConversation}
            className="chat-clear-button"
            title="Clear conversation"
          >
            🗑️
          </button>
        </div>
      </div>
      
      <div className="chat-messages">
        {conversations.length === 0 ? (
          <div className="chat-empty-state">
            <p>Ask the sommelier assistant about wines, food pairings, or recommendations!</p>
          </div>
        ) : (
          conversations.map((msg, index) => (
            <div key={index} className={`message ${msg.role}`}>
              <div 
                className={`message-content ${msg.isTyping ? 'typing' : ''}`}
              >
                {msg.isTyping ? (
                  'Thinking...'
                ) : (
                  <>
                    <div>{msg.content}</div>
                    {msg.role === 'assistant' && msg.isCacheHit !== undefined && (
                      <div className="message-metadata">
                        <CacheHitIndicator isCacheHit={msg.isCacheHit} />
                        <span className="message-time">
                          {msg.isCacheHit 
                            ? `Cache hit (${msg.responseTime.toFixed(2)}s)`
                            : `Generated response (${msg.responseTime.toFixed(2)}s)`}
                        </span>
                        {msg.queryType && (
                          <span className="message-type">
                            {msg.queryType}
                          </span>
                        )}
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          ))
        )}
        <div ref={endOfMessagesRef} />
      </div>
      
      <form onSubmit={handleSubmit} className="chat-input-container">
        <textarea
          ref={textareaRef}
          className="chat-input"
          placeholder="Ask about wines, food pairings, or recommendations..."
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isProcessing}
          rows={1}
        />
        <button 
          type="submit" 
          className="chat-send-button"
          disabled={isProcessing || !query.trim()}
        >
          📤
        </button>
      </form>
    </div>
  );
}

export default ChatPanel;