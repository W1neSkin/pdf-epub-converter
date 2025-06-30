import React, { useState, useCallback } from 'react';
import styled, { createGlobalStyle } from 'styled-components';
import '@fortawesome/fontawesome-free/css/all.min.css';
import EpubReader from './components/EpubReader';
import FileUploader from './components/FileUploader';
import PdfUploader from './components/PdfUploader';
import './App.css';

const GlobalStyle = createGlobalStyle`
  * {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
  }

  body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
  }
`;

const AppContainer = styled.div`
  min-height: 100vh;
  display: flex;
  flex-direction: column;
`;

const Header = styled.header`
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  padding: 1rem 2rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: space-between;
`;

const Logo = styled.h1`
  color: white;
  font-size: 1.8rem;
  font-weight: 300;
  display: flex;
  align-items: center;
  gap: 0.5rem;

  i {
    color: #ffd700;
  }
`;

const MainContent = styled.main`
  flex: 1;
  padding: 2rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
`;

function App() {
  const [epubFile, setEpubFile] = useState(null);
  const [isReading, setIsReading] = useState(false);
  const [showPdfUploader, setShowPdfUploader] = useState(false);

  const handleFileSelect = useCallback((file) => {
    setEpubFile(file);
    setIsReading(true);
  }, []);

  const handleBackToLibrary = useCallback(() => {
    setEpubFile(null);
    setIsReading(false);
    setShowPdfUploader(false);
  }, []);

  const handleShowPdfUploader = useCallback(() => {
    setShowPdfUploader(true);
  }, []);

  const handleShowEpubUploader = useCallback(() => {
    setShowPdfUploader(false);
  }, []);

  return (
    <>
      <GlobalStyle />
      <AppContainer>
        <Header>
          <Logo>
            <i className={showPdfUploader ? "fas fa-file-pdf" : "fas fa-book-open"}></i>
            {showPdfUploader ? "PDF to EPUB Converter" : "EPUB Reader"}
          </Logo>
          {(isReading || showPdfUploader) && (
            <button 
              onClick={handleBackToLibrary}
              style={{
                background: 'rgba(255, 255, 255, 0.2)',
                border: '1px solid rgba(255, 255, 255, 0.3)',
                color: 'white',
                padding: '0.5rem 1rem',
                borderRadius: '0.5rem',
                cursor: 'pointer',
                transition: 'all 0.3s ease'
              }}
              onMouseOver={(e) => e.target.style.background = 'rgba(255, 255, 255, 0.3)'}
              onMouseOut={(e) => e.target.style.background = 'rgba(255, 255, 255, 0.2)'}
            >
              <i className="fas fa-arrow-left"></i> Back to Home
            </button>
          )}
        </Header>
        
        <MainContent>
          {!isReading && !showPdfUploader ? (
            <div>
              <div style={{ 
                display: 'flex', 
                gap: '1rem', 
                marginBottom: '2rem',
                justifyContent: 'center'
              }}>
                <button
                  onClick={handleShowPdfUploader}
                  style={{
                    background: 'linear-gradient(135deg, #ffd700, #ffed4e)',
                    color: '#333',
                    border: 'none',
                    padding: '1rem 2rem',
                    borderRadius: '0.5rem',
                    fontWeight: 'bold',
                    cursor: 'pointer',
                    transition: 'transform 0.2s ease'
                  }}
                  onMouseOver={(e) => e.target.style.transform = 'translateY(-2px)'}
                  onMouseOut={(e) => e.target.style.transform = 'translateY(0)'}
                >
                  <i className="fas fa-file-pdf" style={{ marginRight: '0.5rem' }}></i>
                  Convert PDF to EPUB
                </button>
                <button
                  onClick={handleShowEpubUploader}
                  style={{
                    background: 'rgba(255, 255, 255, 0.2)',
                    border: '1px solid rgba(255, 255, 255, 0.3)',
                    color: 'white',
                    padding: '1rem 2rem',
                    borderRadius: '0.5rem',
                    cursor: 'pointer',
                    transition: 'all 0.3s ease'
                  }}
                  onMouseOver={(e) => e.target.style.background = 'rgba(255, 255, 255, 0.3)'}
                  onMouseOut={(e) => e.target.style.background = 'rgba(255, 255, 255, 0.2)'}
                >
                  <i className="fas fa-book-open" style={{ marginRight: '0.5rem' }}></i>
                  Read EPUB File
                </button>
              </div>
              <FileUploader onFileSelect={handleFileSelect} />
            </div>
          ) : showPdfUploader ? (
            <PdfUploader onBack={handleBackToLibrary} />
          ) : (
            <EpubReader epubFile={epubFile} />
          )}
        </MainContent>
      </AppContainer>
    </>
  );
}

export default App;
