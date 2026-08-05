import React, { useState, useRef, useEffect } from 'react';
import { MoreVertical, FolderOpen, Download } from 'lucide-react';

export function ThreeDotMenu({ onViewFolder, onDownloadZip }) {
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div ref={menuRef} style={{ position: 'relative' }}>
      <button
        type="button"
        className="tile-menu-btn"
        onClick={(e) => {
          e.stopPropagation();
          setIsOpen(!isOpen);
        }}
        aria-label="Options"
      >
        <MoreVertical size={18} />
      </button>

      {isOpen && (
        <div className="dropdown-menu">
          <button
            type="button"
            className="dropdown-item"
            onClick={(e) => {
              e.stopPropagation();
              setIsOpen(false);
              onViewFolder();
            }}
          >
            <FolderOpen size={16} color="#6366f1" />
            <span>View folder</span>
          </button>

          <button
            type="button"
            className="dropdown-item"
            onClick={(e) => {
              e.stopPropagation();
              setIsOpen(false);
              onDownloadZip();
            }}
          >
            <Download size={16} color="#06b6d4" />
            <span>Download zip</span>
          </button>
        </div>
      )}
    </div>
  );
}
