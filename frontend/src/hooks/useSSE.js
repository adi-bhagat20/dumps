import { useState, useEffect } from 'react';

export function useSSE(jobId, { onProgress, onComplete, onError }) {
  const [isConnecting, setIsConnecting] = useState(false);

  useEffect(() => {
    if (!jobId) return;

    setIsConnecting(true);
    const eventSource = new EventSource(`/api/jobs/${jobId}/stream`);

    eventSource.onopen = () => {
      setIsConnecting(false);
    };

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'progress') {
          onProgress?.(data.processed, data.total);
        } else if (data.type === 'completed') {
          onComplete?.(data.clusters);
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
      // EventSource will automatically retry connecting if needed
    };

    return () => {
      eventSource.close();
    };
  }, [jobId]);

  return { isConnecting };
}
