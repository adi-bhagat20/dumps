import { useState, useEffect } from 'react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

export function useSSE(jobId, { onProgress, onComplete, onError }) {
  const [isConnecting, setIsConnecting] = useState(false);

  useEffect(() => {
    if (!jobId) return;

    setIsConnecting(true);
    const streamUrl = `${API_BASE}/api/jobs/${jobId}/stream`;
    const eventSource = new EventSource(streamUrl);

    eventSource.onopen = () => {
      setIsConnecting(false);
    };

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'progress') {
          onProgress?.(data.processed, data.total);
        } else if (data.type === 'completed') {
          // Format thumbnail URLs if API_BASE is set
          const clusters = (data.clusters || []).map(c => ({
            ...c,
            thumbnail_url: c.thumbnail_url ? (c.thumbnail_url.startsWith('http') ? c.thumbnail_url : `${API_BASE}${c.thumbnail_url}`) : null
          }));
          onComplete?.(clusters);
          eventSource.close();
        } else if (data.type === 'error') {
          onError?.(data.error || 'Processing failed');
          eventSource.close();
        }
      } catch (err) {
        console.error('Failed to parse SSE event:', err);
      }
    };

    eventSource.onerror = (err) => {
      console.error('SSE connection error:', err);
      setIsConnecting(false);
    };

    return () => {
      eventSource.close();
    };
  }, [jobId]);

  return { isConnecting };
}
