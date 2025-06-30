import React, { useState, useEffect, useRef, useCallback } from 'react';
import styled from 'styled-components';

const ViewerContainer = styled.div`
  width: 100%;
  height: 100%;
  overflow: auto;
  position: relative;
  background: white;
`;

const PageContent = styled.div`
  max-width: 100%;
  margin: 0 auto;
  padding: 1rem;
  line-height: 1.6;
  color: #333;
  min-height: 100%;
  box-sizing: border-box;

  /* PDF Page Container Styles */
  .page-container {
    position: relative;
    margin: 0 auto 40px auto;
    max-width: 100%;
    border: 1px solid #ccc;
    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
  }

  .page-image {
    width: 100%;
    height: auto;
    display: block;
  }

  .text-layer {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    pointer-events: none;
  }

  .text-element {
    position: absolute;
    color: rgba(0, 0, 0, 0.1);
    user-select: text;
    pointer-events: auto;
    z-index: 10;
    margin: 0;
    padding: 0;
    line-height: 1;
    white-space: nowrap;
    border: 1px solid rgba(0, 0, 0, 0.05);
    cursor: text;
    font-family: inherit;
  }

  .text-element:hover {
    background-color: rgba(255, 255, 0, 0.3);
    color: rgba(0, 0, 0, 0.8);
    border: 1px solid rgba(255, 255, 0, 0.6);
  }

  .text-element:focus,
  .text-element:active {
    background-color: rgba(0, 123, 255, 0.3);
    color: rgba(0, 0, 0, 0.9);
    border: 1px solid rgba(0, 123, 255, 0.6);
  }

  .page-info {
    text-align: center;
    margin-bottom: 20px;
    padding: 10px;
    background-color: #f8f9fa;
    border-radius: 4px;
    border: 1px solid #dee2e6;
  }

  /* Regular EPUB content styling for non-PDF content */
  h1, h2, h3, h4, h5, h6 {
    margin: 1.5rem 0 1rem;
    color: #2c3e50;
    line-height: 1.3;
  }

  h1 { font-size: 2rem; }
  h2 { font-size: 1.5rem; }
  h3 { font-size: 1.25rem; }

  p {
    margin: 1rem 0;
  }

  /* Regular images (not page images) */
  img:not(.page-image) {
    max-width: 100%;
    height: auto;
    display: block;
    margin: 1rem auto;
    border-radius: 0.5rem;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }

  blockquote {
    border-left: 4px solid #3498db;
    margin: 1.5rem 0;
    padding: 1rem 1.5rem;
    background: #f8f9fa;
    font-style: italic;
  }

  code {
    background: #f8f9fa;
    padding: 0.2rem 0.4rem;
    border-radius: 0.25rem;
    font-family: 'Courier New', monospace;
    font-size: 0.9em;
  }

  pre {
    background: #f8f9fa;
    padding: 1rem;
    border-radius: 0.5rem;
    overflow-x: auto;
    margin: 1rem 0;
  }

  ul, ol {
    margin: 1rem 0;
    padding-left: 2rem;
  }

  li {
    margin: 0.5rem 0;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    margin: 1rem 0;
  }

  th, td {
    border: 1px solid #ddd;
    padding: 0.75rem;
    text-align: left;
  }

  th {
    background: #f8f9fa;
    font-weight: 600;
  }

  /* Text selection styling */
  ::selection {
    background: rgba(52, 152, 219, 0.3);
  }

  ::-moz-selection {
    background: rgba(52, 152, 219, 0.3);
  }

  /* Custom scrollbar */
  &::-webkit-scrollbar {
    width: 8px;
  }

  &::-webkit-scrollbar-track {
    background: #f1f1f1;
  }

  &::-webkit-scrollbar-thumb {
    background: #c1c1c1;
    border-radius: 4px;
  }

  &::-webkit-scrollbar-thumb:hover {
    background: #a1a1a1;
  }
`;

const NavigationOverlay = styled.div`
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  pointer-events: none;
`;

const NavArea = styled.div`
  flex: 1;
  pointer-events: auto;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.2s ease;

  &:hover {
    background: rgba(0, 0, 0, 0.05);
  }

  &:first-child {
    justify-content: flex-start;
    padding-left: 2rem;
  }

  &:last-child {
    justify-content: flex-end;
    padding-right: 2rem;
  }
`;

const NavIcon = styled.i`
  font-size: 2rem;
  color: rgba(0, 0, 0, 0.3);
  opacity: 0;
  transition: opacity 0.2s ease;

  ${NavArea}:hover & {
    opacity: 1;
  }
`;

const PageViewer = ({ pages, currentPageIndex, epubData, onPageChange }) => {
  const [processedContent, setProcessedContent] = useState('');
  const containerRef = useRef();

  const processPageContent = useCallback(async (page) => {
    if (!page || !page.content) {
      setProcessedContent('<div>No content available</div>');
      return;
    }

    try {
      // Parse the HTML content
      const parser = new DOMParser();
      const doc = parser.parseFromString(page.content, 'text/html');
      
      // Process images if they exist in the EPUB
      if (epubData && epubData.zip) {
        const images = doc.querySelectorAll('img');
        for (let img of images) {
          const src = img.getAttribute('src');
          if (src && !src.startsWith('http') && !src.startsWith('data:')) {
            try {
              // Construct the full path relative to the EPUB structure
              const fullPath = epubData.opfBasePath + src;
              const imageFile = epubData.zip.file(fullPath);
              
              if (imageFile) {
                const imageBlob = await imageFile.async('blob');
                const imageUrl = URL.createObjectURL(imageBlob);
                img.src = imageUrl;
              }
            } catch (err) {
              console.warn('Could not load image:', src, err);
            }
          }
        }
      }

      // Check if this is a PDF-converted page with overlay structure
      const pageContainer = doc.querySelector('.page-container');
      const textLayer = doc.querySelector('.text-layer');
      
      if (pageContainer && textLayer) {
        // This is a PDF page with text overlay - preserve the entire structure
        const bodyContent = doc.body ? doc.body.innerHTML : doc.documentElement.innerHTML;
        setProcessedContent(bodyContent);
      } else {
        // Regular EPUB content - extract body content as before
        const bodyContent = doc.body ? doc.body.innerHTML : doc.documentElement.innerHTML;
        setProcessedContent(bodyContent);
      }
      
      // Scroll to top when page changes
      if (containerRef.current) {
        containerRef.current.scrollTop = 0;
      }
    } catch (err) {
      console.error('Error processing page content:', err);
      setProcessedContent('<div>Error loading page content</div>');
    }
  }, [epubData]);

  useEffect(() => {
    if (pages && pages[currentPageIndex]) {
      processPageContent(pages[currentPageIndex]);
    }
  }, [pages, currentPageIndex, processPageContent]);

  const handlePreviousPage = useCallback(() => {
    if (currentPageIndex > 0) {
      onPageChange(currentPageIndex - 1);
    }
  }, [currentPageIndex, onPageChange]);

  const handleNextPage = useCallback(() => {
    if (currentPageIndex < pages.length - 1) {
      onPageChange(currentPageIndex + 1);
    }
  }, [currentPageIndex, pages.length, onPageChange]);

  // Handle keyboard navigation
  useEffect(() => {
    const handleKeyPress = (e) => {
      if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
        handlePreviousPage();
      } else if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
        handleNextPage();
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [handlePreviousPage, handleNextPage]);

  if (!pages || pages.length === 0) {
    return (
      <ViewerContainer>
        <PageContent>
          <div style={{ textAlign: 'center', padding: '2rem', color: '#666' }}>
            No pages to display
          </div>
        </PageContent>
      </ViewerContainer>
    );
  }

  return (
    <ViewerContainer ref={containerRef}>
      <PageContent 
        dangerouslySetInnerHTML={{ __html: processedContent }}
      />
      
      <NavigationOverlay>
        <NavArea onClick={handlePreviousPage} style={{ cursor: currentPageIndex === 0 ? 'default' : 'pointer' }}>
          {currentPageIndex > 0 && (
            <NavIcon className="fas fa-chevron-left" />
          )}
        </NavArea>
        
        <NavArea onClick={handleNextPage} style={{ cursor: currentPageIndex >= pages.length - 1 ? 'default' : 'pointer' }}>
          {currentPageIndex < pages.length - 1 && (
            <NavIcon className="fas fa-chevron-right" />
          )}
        </NavArea>
      </NavigationOverlay>
    </ViewerContainer>
  );
};

export default PageViewer; 