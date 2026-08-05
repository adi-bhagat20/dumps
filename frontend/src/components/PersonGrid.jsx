import React from 'react';
import { PersonTile } from './PersonTile';

export function PersonGrid({ clusters, onViewFolder, onDownloadZip }) {
  if (!clusters || clusters.length === 0) return null;

  const totalPhotos = clusters.reduce((acc, c) => acc + c.photo_count, 0);

  return (
    <section className="results-section">
      <div className="results-header">
        <div>
          <h2 className="results-title">Auto-Sorted Collections</h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.95rem', marginTop: '4px' }}>
            Found {clusters.filter(c => c.cluster_id !== 'unsorted').length} distinct people across {totalPhotos} photos
          </p>
        </div>
      </div>

      <div className="person-grid">
        {clusters.map((cluster) => (
          <PersonTile
            key={cluster.cluster_id}
            cluster={cluster}
            onViewFolder={() => onViewFolder(cluster)}
            onDownloadZip={() => onDownloadZip(cluster)}
          />
        ))}
      </div>
    </section>
  );
}
