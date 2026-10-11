import React, { useState } from 'react';
import { Header } from './components/Header';
import { UploadZone } from './components/UploadZone';
import { ProgressBar } from './components/ProgressBar';
import { PersonGrid } from './components/PersonGrid';
import { PhotoGallery } from './components/PhotoGallery';
import { uploadFolder, startJob, getClusterZipUrl, ensureServerAwake } from './lib/api';
import { useSSE } from './hooks/useSSE';

export function App() {
  const [stage, setStage] = useState('idle'); // 'idle' | 'uploading' | 'processing' | 'completed' | 'error'
  const [isUploading, setIsUploading] = useState(false);
  const [statusMessage, setStatusMessage] = useState('');
  const [jobId, setJobId] = useState(null);
  const [progress, setProgress] = useState({ processed: 0, total: 0 });
  const [clusters, setClusters] = useState([]);
  const [errorMessage, setErrorMessage] = useState('');
  const [activeGalleryCluster, setActiveGalleryCluster] = useState(null);

  // Hook up real-time SSE progress & completion
  useSSE(jobId, {
    onProgress: (processed, total) => {
      setProgress({ processed, total });
      setStage('processing');
    },
    onComplete: (clusterData) => {
      setClusters(clusterData);
      setStage('completed');
    },
    onError: (err) => {
      setErrorMessage(err);
      setStage('error');
    }
  });

  const handleGenerate = async (files, folderName) => {
    try {
      setErrorMessage('');
      setIsUploading(true);
      setStage('uploading');
      setStatusMessage('Checking server status...');

      // 1. Ensure backend is awake (handles free-tier cold starts gracefully)
      await ensureServerAwake((msg) => setStatusMessage(msg));

      setStatusMessage(`Uploading ${files.length} photos...`);
      // 2. Upload folder of files to backend
      const uploadRes = await uploadFolder(files, folderName);

      setStatusMessage('Starting AI face clustering pipeline...');
      // 3. Start async face clustering job
      const jobRes = await startJob(uploadRes.upload_id);
      
      setJobId(jobRes.job_id);
      setProgress({ processed: 0, total: uploadRes.file_count });
      setIsUploading(false);
      setStatusMessage('');
      setStage('processing');
    } catch (err) {
      console.error('Error starting pipeline:', err);
      setErrorMessage(err.message || 'Failed to upload and start processing.');
      setIsUploading(false);
      setStatusMessage('');
      setStage('error');
    }
  };

  const handleViewFolder = (cluster) => {
    setActiveGalleryCluster(cluster);
  };

  const handleDownloadZip = (cluster) => {
    const zipUrl = getClusterZipUrl(jobId, cluster.cluster_id);
    const link = document.createElement('a');
    link.href = zipUrl;
    link.download = `dumps_${cluster.label.replace(/\s+/g, '_').toLowerCase()}.zip`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleReset = () => {
    setStage('idle');
    setJobId(null);
    setProgress({ processed: 0, total: 0 });
    setClusters([]);
    setErrorMessage('');
    setActiveGalleryCluster(null);
  };

  return (
    <div className="app-container">
      <Header />

      <main>
        <div className="hero-section">
          <h1 className="hero-title">Auto-Sort Event Photos by Person</h1>
          <p className="hero-subtitle">
            Upload a folder of mixed photos and get back per-person sub-collections, 
            each downloadable as a zip — zero manual tagging required.
          </p>
        </div>

        {stage !== 'completed' && (
          <UploadZone
            onGenerate={handleGenerate}
            isUploading={isUploading}
          />
        )}

        {(stage === 'processing' || stage === 'uploading') && (
          <ProgressBar
            processed={progress.processed}
            total={progress.total}
            title={stage === 'uploading' ? (statusMessage || "Preparing Upload...") : "Analyzing & Clustering Photos..."}
            statusText={stage === 'uploading' ? statusMessage : undefined}
          />
        )}

        {stage === 'error' && (
          <div className="glass-panel" style={{ padding: '24px', marginTop: '24px', borderColor: '#ef4444', color: '#ef4444', textAlign: 'center' }}>
            <p style={{ fontWeight: '600', marginBottom: '8px' }}>Processing Error</p>
            <p style={{ fontSize: '0.9rem' }}>{errorMessage}</p>
            <button
              type="button"
              className="btn-primary"
              onClick={handleReset}
              style={{ marginTop: '16px' }}
            >
              Try Again
            </button>
          </div>
        )}

        {stage === 'completed' && (
          <>
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '16px' }}>
              <button
                type="button"
                className="sample-link"
                onClick={handleReset}
              >
                Sort Another Folder
              </button>
            </div>

            <PersonGrid
              clusters={clusters}
              onViewFolder={handleViewFolder}
              onDownloadZip={handleDownloadZip}
            />
          </>
        )}
      </main>

      {activeGalleryCluster && (
        <PhotoGallery
          jobId={jobId}
          cluster={activeGalleryCluster}
          onClose={() => setActiveGalleryCluster(null)}
        />
      )}

      <footer className="privacy-notice">
        <p>Your photos are automatically deleted after 24 hours. Privacy first.</p>
      </footer>
    </div>
  );
}
