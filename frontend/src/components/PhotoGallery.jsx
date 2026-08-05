import React, { useEffect, useState } from 'react';
import { X, Download, Loader2 } from 'lucide-react';
import { getClusterPhotos, getClusterZipUrl } from '../lib/api';

export function PhotoGallery({ jobId, cluster, onClose }) {
  const [photos, setPhotos] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!jobId || !cluster) return;

    let isMounted = true;
    setLoading(true);

    getClusterPhotos(jobId, cluster.cluster_id)
      .then((data) => {
        if (isMounted) {
          setPhotos(data.photos || []);
          setLoading(false);
        }
      })
      .catch((err) => {
        console.error('Failed to load photos:', err);
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [jobId, cluster]);

  // ESC key handler to close modal
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (!cluster) return null;

  const zipUrl = getClusterZipUrl(jobId, cluster.cluster_id);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="glass-panel modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <h2 className="modal-title">{cluster.label}</h2>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              {cluster.photo_count} photos assigned
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <a
              href={zipUrl}
              download
              className="btn-primary"
              style={{ padding: '8px 16px', fontSize: '0.875rem' }}
            >
              <Download size={16} />
              <span>Download zip</span>
            </a>

            <button type="button" className="modal-close-btn" onClick={onClose}>
              <X size={22} />
            </button>
          </div>
        </div>

        {loading ? (
          <div style={{ padding: '60px', textAlign: 'center', color: 'var(--text-muted)' }}>
            <Loader2 size={36} className="animate-spin" style={{ margin: '0 auto 12px auto' }} />
            <p>Loading photos...</p>
          </div>
        ) : (
          <div className="gallery-grid">
            {photos.map((photo) => (
              <div key={photo.photo_key} className="gallery-item">
                <img
                  src={photo.url}
                  alt={photo.filename}
                  className="gallery-img"
                  loading="lazy"
                />
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
