import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import './i18n';
import './styles/global.css';

// Global Style Reset and Base Styles
const globalStyles = `
  *, *::before, *::after { 
    box-sizing: border-box; 
    margin: 0; 
    padding: 0; 
  }

  body { 
    background: #f8fafc; 
    font-family: 'DM Sans', sans-serif; 
    color: #111827;
    line-height: 1.6;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }

  h1, h2, h3, h4, h5, h6 {
    font-family: 'Outfit', sans-serif;
    color: #111827;
  }

  input, button, select, textarea { 
    font-family: inherit; 
  }

  ::-webkit-scrollbar { 
    width: 6px; 
  }

  ::-webkit-scrollbar-track { 
    background: #f1f5f9; 
  }

  ::-webkit-scrollbar-thumb { 
    background: #cbd5e1; 
    border-radius: 3px; 
  }

  ::-webkit-scrollbar-thumb:hover { 
    background: #94a3b8; 
  }

  input:focus, select:focus, textarea:focus { 
    outline: none; 
    border-color: #1a56db !important; 
    box-shadow: 0 0 0 3px rgba(26,86,219,0.12) !important; 
  }

  .glass-card {
    background: #ffffff;
    border-radius: 20px;
    box-shadow: 0 2px 8px rgba(17,24,39,0.06), 0 8px 32px rgba(17,24,39,0.08);
    border: 1px solid #eef2fb;
  }
`;

const styleEl = document.createElement('style');
styleEl.innerHTML = globalStyles;
document.head.appendChild(styleEl);

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);
