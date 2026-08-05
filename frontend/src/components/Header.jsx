import React from 'react';
import { Layers, Download } from 'lucide-react';

export function Header() {
  return (
    <header className="header-container">
      <div className="logo-group">
        <div className="logo-badge">
          <Layers size={24} color="#ffffff" />
        </div>
        <span className="logo-text">DUMPS</span>
      </div>

      <a
        href="#"
        onClick={(e) => {
          e.preventDefault();
          alert("Sample photo folder: Upload your 28 sample photos folder directly using the folder picker below!");
        }}
        className="sample-link"
        title="Download sample folder to test"
      >
        <Download size={16} />
        <span>Download sample folder</span>
      </a>
    </header>
  );
}
