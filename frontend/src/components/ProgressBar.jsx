import React from 'react';

export function ProgressBar({ processed, total, statusText, title }) {
  const percentage = total > 0 ? Math.min(100, Math.round((processed / total) * 100)) : 0;

  return (
    <div className="glass-panel progress-card">
      <div className="progress-header">
        <span className="progress-title">{title || "Analyzing & Clustering Photos..."}</span>
        <span className="progress-counter">
          {processed} / {total} photos analyzed ({percentage}%)
        </span>
      </div>

      <div className="progress-bar-bg">
        <div
          className="progress-bar-fill"
          style={{ width: `${percentage}%` }}
        />
      </div>

      <p style={{ marginTop: '16px', fontSize: '0.85rem', color: 'var(--text-muted)', textAlign: 'center' }}>
        {statusText || "Detecting faces, deduplicating, and computing DBSCAN clusters..."}
      </p>
    </div>
  );
}
