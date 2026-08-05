import React from 'react';
import { User, HelpCircle } from 'lucide-react';
import { ThreeDotMenu } from './ThreeDotMenu';

export function PersonTile({ cluster, onViewFolder, onDownloadZip }) {
  const isUnsorted = cluster.cluster_id === 'unsorted';

  return (
    <div
      className="glass-panel person-card"
      onClick={onViewFolder}
      style={{ cursor: 'pointer' }}
    >
      <ThreeDotMenu
        onViewFolder={onViewFolder}
        onDownloadZip={onDownloadZip}
      />

      <div className="avatar-container" style={{ borderColor: isUnsorted ? 'var(--text-dim)' : 'var(--accent-primary)' }}>
        {cluster.thumbnail_url ? (
          <img
            src={cluster.thumbnail_url}
            alt={cluster.label}
            className="avatar-img"
            onError={(e) => {
              e.target.onerror = null;
              e.target.style.display = 'none';
            }}
          />
        ) : isUnsorted ? (
          <HelpCircle size={40} className="avatar-placeholder" />
        ) : (
          <User size={40} className="avatar-placeholder" />
        )}
      </div>

      <h3 className="person-name">{cluster.label}</h3>

      <div className="photo-count-badge">
        {cluster.photo_count} {cluster.photo_count === 1 ? 'photo' : 'photos'}
      </div>
    </div>
  );
}
