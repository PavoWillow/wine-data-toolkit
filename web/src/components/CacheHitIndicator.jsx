// src/components/CacheHitIndicator.jsx
function CacheHitIndicator({ isCacheHit }) {
  if (isCacheHit) {
    return (
      <div className="cache-hit-indicator" title="Cache Hit - Fast Response">
        ⚡
      </div>
    );
  }
  
  return (
    <div className="cache-hit-indicator" title="Generated Response">
      🔄
    </div>
  );
}

export default CacheHitIndicator;