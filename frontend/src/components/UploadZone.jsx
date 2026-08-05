import React, { useRef, useState } from 'react';
import { FolderUp, Sparkles, FolderCheck, AlertCircle } from 'lucide-react';

const ALLOWED_EXTENSIONS = ['jpg', 'jpeg', 'png', 'heic'];

export function UploadZone({ onGenerate, isUploading }) {
  const fileInputRef = useRef(null);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [folderName, setFolderName] = useState('');
  const [warning, setWarning] = useState('');
  const [isDragActive, setIsDragActive] = useState(false);

  const handleFileChange = (e) => {
    const files = Array.from(e.target.files || []);
    processFiles(files);
  };

  const processFiles = (files) => {
    setWarning('');
    if (!files.length) {
      setWarning('Selected folder is empty.');
      setSelectedFiles([]);
      return;
    }

    // Filter for image files only
    const validImages = files.filter(f => {
      const ext = f.name.split('.').pop().toLowerCase();
      return ALLOWED_EXTENSIONS.includes(ext);
    });

    if (validImages.length === 0) {
      setWarning('No supported image files (JPG, PNG, HEIC) found in the selected folder.');
      setSelectedFiles([]);
      return;
    }

    // Determine folder name from webkitRelativePath or first file path
    let folder = 'Photos';
    if (validImages[0]?.webkitRelativePath) {
      folder = validImages[0].webkitRelativePath.split('/')[0];
    }

    setFolderName(folder);
    setSelectedFiles(validImages);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragActive(true);
  };

  const handleDragLeave = () => {
    setIsDragActive(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragActive(false);
    if (e.dataTransfer.files) {
      processFiles(Array.from(e.dataTransfer.files));
    }
  };

  const handleGenerateClick = () => {
    if (selectedFiles.length > 0) {
      onGenerate(selectedFiles, folderName);
    }
  };

  return (
    <div className="glass-panel upload-zone-container" style={{ padding: '8px' }}>
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        webkitdirectory=""
        directory=""
        multiple
        style={{ display: 'none' }}
        accept="image/jpeg,image/png,image/heic,image/heif,.jpg,.jpeg,.png,.heic"
      />

      <div
        className={`glass-panel upload-zone ${isDragActive ? 'drag-active' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <div className="upload-icon-box">
          <FolderUp size={32} />
        </div>
        <h2 className="upload-title">Choose or drag a photo folder</h2>
        <p className="upload-hint">
          Supports JPG, PNG, and HEIC files • Folder of 100-300 mixed photos
        </p>

        <button
          type="button"
          className="btn-primary"
          onClick={(e) => {
            e.stopPropagation();
            fileInputRef.current?.click();
          }}
        >
          Select Folder
        </button>
      </div>

      {warning && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#ef4444', margin: '16px', fontSize: '0.9rem' }}>
          <AlertCircle size={18} />
          <span>{warning}</span>
        </div>
      )}

      {selectedFiles.length > 0 && (
        <div className="selected-summary">
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <FolderCheck size={24} color="#6366f1" />
            <div>
              <div style={{ fontWeight: '600', fontSize: '1rem' }}>{folderName}</div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                {selectedFiles.length} photos ready for auto-sorting
              </div>
            </div>
          </div>

          <button
            type="button"
            className="btn-primary"
            onClick={handleGenerateClick}
            disabled={isUploading}
          >
            <Sparkles size={18} />
            <span>{isUploading ? 'Uploading...' : 'Generate Clusters'}</span>
          </button>
        </div>
      )}
    </div>
  );
}
