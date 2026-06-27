import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import { AuthProvider } from './context/AuthContext';
import { MT5Provider } from './context/MT5Context';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <AuthProvider>
      <MT5Provider>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </MT5Provider>
    </AuthProvider>
  </React.StrictMode>
);
