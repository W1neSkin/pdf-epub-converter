import React, { useState, useEffect, useCallback } from 'react';
import styled from 'styled-components';
import JSZip from 'jszip';
import TableOfContents from './TableOfContents';
import PageViewer from './PageViewer';
import ReaderControls from './ReaderControls';

const ReaderContainer = styled.div`
  display: flex;
  width: 100%;
  max-width: 1400px;
  height: 80vh;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-radius: 1rem;
  border: 1px solid rgba(255, 255, 255, 0.2);
  overflow: hidden;
`;

const Sidebar = styled.aside`
  width: ${props => props.isOpen ? '300px' : '0'};
  transition: width 0.3s ease;
  background: rgba(0, 0, 0, 0.2);
  border-right: 1px solid rgba(255, 255, 255, 0.1);
  overflow: hidden;
`;

const MainArea = styled.div`
  flex: 1;
  display: flex;
  flex-direction: column;
`;

const ContentArea = styled.div`
  flex: 1;
  overflow: hidden;
  position: relative;
`;

const LoadingOverlay = styled.div`
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(5px);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: white;
  z-index: 1000;
`;

const LoadingSpinner = styled.div`
  width: 50px;
  height: 50px;
  border: 3px solid rgba(255, 255, 255, 0.3);
  border-top: 3px solid #ffd700;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 1rem;

  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
`;

const EpubReader = ({ epubFile }) => {
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [epubData, setEpubData] = useState(null);
  const [currentPageIndex, setCurrentPageIndex] = useState(0);
  const [isTocOpen, setIsTocOpen] = useState(true);
  const [pages, setPages] = useState([]);
  const [bookMetadata, setBookMetadata] = useState({});

  const parseEpub = useCallback(async (file) => {
    try {
      setIsLoading(true);
      setError(null);

      const zip = new JSZip();
      const zipContent = await zip.loadAsync(file);
      
      // Read container.xml to find the content.opf file
      const containerXml = await zipContent.file('META-INF/container.xml').async('text');
      const parser = new DOMParser();
      const containerDoc = parser.parseFromString(containerXml, 'application/xml');
      const rootfile = containerDoc.querySelector('rootfile');
      const opfPath = rootfile.getAttribute('full-path');
      
      // Read the content.opf file
      const opfContent = await zipContent.file(opfPath).async('text');
      const opfDoc = parser.parseFromString(opfContent, 'application/xml');
      
      // Extract metadata
      const metadata = {
        title: opfDoc.querySelector('title')?.textContent || 'Unknown Title',
        creator: opfDoc.querySelector('creator')?.textContent || 'Unknown Author',
        description: opfDoc.querySelector('description')?.textContent || '',
        language: opfDoc.querySelector('language')?.textContent || 'en'
      };
      setBookMetadata(metadata);

      // Extract manifest items
      const manifest = {};
      const manifestItems = opfDoc.querySelectorAll('manifest item');
      manifestItems.forEach(item => {
        manifest[item.getAttribute('id')] = {
          href: item.getAttribute('href'),
          mediaType: item.getAttribute('media-type')
        };
      });

      // Extract spine (reading order)
      const spine = [];
      const spineItems = opfDoc.querySelectorAll('spine itemref');
      spineItems.forEach(item => {
        const idref = item.getAttribute('idref');
        if (manifest[idref]) {
          spine.push({
            id: idref,
            href: manifest[idref].href,
            mediaType: manifest[idref].mediaType
          });
        }
      });

      // Read all HTML content files
      const opfBasePath = opfPath.substring(0, opfPath.lastIndexOf('/') + 1);
      const pagesData = [];
      
      for (let i = 0; i < spine.length; i++) {
        const item = spine[i];
        if (item.mediaType === 'application/xhtml+xml') {
          try {
            const fullPath = opfBasePath + item.href;
            const htmlContent = await zipContent.file(fullPath).async('text');
            pagesData.push({
              id: item.id,
              href: item.href,
              content: htmlContent,
              title: `Page ${i + 1}`
            });
          } catch (err) {
            console.warn(`Could not load page: ${item.href}`, err);
          }
        }
      }

      setPages(pagesData);
      setEpubData({ zip: zipContent, manifest, spine, metadata, opfBasePath });
      setCurrentPageIndex(0);
      
    } catch (err) {
      console.error('Error parsing EPUB:', err);
      setError('Failed to parse EPUB file. Please ensure it\'s a valid EPUB format.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (epubFile) {
      parseEpub(epubFile);
    }
  }, [epubFile, parseEpub]);

  const handlePageChange = useCallback((pageIndex) => {
    if (pageIndex >= 0 && pageIndex < pages.length) {
      setCurrentPageIndex(pageIndex);
    }
  }, [pages.length]);

  const handleTocToggle = useCallback(() => {
    setIsTocOpen(prev => !prev);
  }, []);

  if (error) {
    return (
      <ReaderContainer>
        <ContentArea>
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center', 
            height: '100%', 
            color: 'white',
            textAlign: 'center',
            padding: '2rem'
          }}>
            <div>
              <i className="fas fa-exclamation-triangle" style={{ fontSize: '3rem', marginBottom: '1rem', color: '#ff6b6b' }}></i>
              <h3 style={{ marginBottom: '1rem' }}>Error Loading EPUB</h3>
              <p>{error}</p>
            </div>
          </div>
        </ContentArea>
      </ReaderContainer>
    );
  }

  return (
    <ReaderContainer>
      {isLoading && (
        <LoadingOverlay>
          <LoadingSpinner />
          <div>Loading EPUB...</div>
        </LoadingOverlay>
      )}
      
      <Sidebar isOpen={isTocOpen}>
        <TableOfContents 
          pages={pages}
          currentPageIndex={currentPageIndex}
          onPageSelect={handlePageChange}
          bookMetadata={bookMetadata}
        />
      </Sidebar>
      
      <MainArea>
        <ReaderControls
          currentPageIndex={currentPageIndex}
          totalPages={pages.length}
          onPageChange={handlePageChange}
          onTocToggle={handleTocToggle}
          isTocOpen={isTocOpen}
          bookTitle={bookMetadata.title}
        />
        
        <ContentArea>
          <PageViewer
            pages={pages}
            currentPageIndex={currentPageIndex}
            epubData={epubData}
            onPageChange={handlePageChange}
          />
        </ContentArea>
      </MainArea>
    </ReaderContainer>
  );
};

export default EpubReader; 