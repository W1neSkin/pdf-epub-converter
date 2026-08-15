import React, { useCallback, useEffect, useState } from 'react';
import styled from 'styled-components';
import JSZip from 'jszip';
import TableOfContents from './TableOfContents';
import PageViewer from './PageViewer';
import ReaderControls from './ReaderControls';

const ReaderContainer = styled.div`
  display: flex;
  width: 100%;
  max-width: 1400px;
  min-height: 78vh;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(12px);
  border-radius: 1rem;
  border: 1px solid rgba(255, 255, 255, 0.2);
  overflow: hidden;
  position: relative;
`;

const Sidebar = styled.aside`
  width: ${(props) => (props.$isOpen ? '300px' : '0')};
  transition: width 0.25s ease;
  background: rgba(17, 24, 39, 0.45);
  border-right: 1px solid rgba(255, 255, 255, 0.1);
  overflow: hidden;

  @media (max-width: 900px) {
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: ${(props) => (props.$isOpen ? '280px' : '0')};
    z-index: 20;
  }
`;

const MainArea = styled.div`
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
`;

const ContentArea = styled.div`
  flex: 1;
  overflow: hidden;
  position: relative;
`;

const CenteredState = styled.div`
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  text-align: center;
  padding: 2rem;
`;

const ActionButton = styled.button`
  margin-top: 1rem;
  background: rgba(255, 255, 255, 0.16);
  color: white;
  border: 1px solid rgba(255, 255, 255, 0.35);
  border-radius: 0.5rem;
  padding: 0.6rem 1rem;
  cursor: pointer;
`;

function resolveZipPath(basePath, href) {
  const cleanHref = (href || '').split('#')[0].split('?')[0];
  const combined = `${basePath || ''}${cleanHref}`;
  const parts = [];
  combined.split('/').forEach((part) => {
    if (!part || part === '.') return;
    if (part === '..') {
      parts.pop();
      return;
    }
    parts.push(part);
  });
  return parts.join('/');
}

function readMetadataTag(doc, tagName, fallback = '') {
  const namespaced = doc.getElementsByTagNameNS('*', tagName);
  if (namespaced.length > 0) {
    const text = namespaced[0].textContent?.trim();
    if (text) return text;
  }
  const simple = doc.getElementsByTagName(tagName);
  if (simple.length > 0) {
    const text = simple[0].textContent?.trim();
    if (text) return text;
  }
  return fallback;
}

const EpubReader = ({ epubFile, epubUrl, token, onBack }) => {
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [epubData, setEpubData] = useState(null);
  const [pages, setPages] = useState([]);
  const [bookMetadata, setBookMetadata] = useState({});
  const [currentPageIndex, setCurrentPageIndex] = useState(0);
  const [isTocOpen, setIsTocOpen] = useState(true);

  const parseEpub = useCallback(async (fileBlob) => {
    setIsLoading(true);
    setError('');
    try {
      const zip = await JSZip.loadAsync(fileBlob);
      const containerFile = zip.file('META-INF/container.xml');
      if (!containerFile) {
        throw new Error('container.xml is missing');
      }
      const containerXml = await containerFile.async('text');
      const xmlParser = new DOMParser();
      const containerDoc = xmlParser.parseFromString(containerXml, 'application/xml');
      const rootfile = containerDoc.querySelector('rootfile');
      const opfPath = rootfile?.getAttribute('full-path');
      if (!opfPath) {
        throw new Error('OPF path not found');
      }

      const opfFile = zip.file(opfPath);
      if (!opfFile) {
        throw new Error('content.opf not found in ZIP');
      }
      const opfContent = await opfFile.async('text');
      const opfDoc = xmlParser.parseFromString(opfContent, 'application/xml');
      const opfBasePath = opfPath.includes('/')
        ? opfPath.slice(0, opfPath.lastIndexOf('/') + 1)
        : '';

      const metadata = {
        title: readMetadataTag(opfDoc, 'title', 'Unknown Title'),
        creator: readMetadataTag(opfDoc, 'creator', 'Unknown Author'),
        description: readMetadataTag(opfDoc, 'description', ''),
        language: readMetadataTag(opfDoc, 'language', 'en'),
      };
      setBookMetadata(metadata);

      const manifest = {};
      opfDoc.querySelectorAll('manifest item').forEach((item) => {
        manifest[item.getAttribute('id')] = {
          href: item.getAttribute('href'),
          mediaType: item.getAttribute('media-type'),
          properties: item.getAttribute('properties') || '',
        };
      });

      const cssParts = [];
      for (const item of Object.values(manifest)) {
        if (item.mediaType !== 'text/css') continue;
        const cssPath = resolveZipPath(opfBasePath, item.href);
        const cssFile = zip.file(cssPath);
        if (!cssFile) continue;
        cssParts.push(await cssFile.async('text'));
      }

      const htmlParser = new DOMParser();
      const pagesData = [];
      const spineItems = opfDoc.querySelectorAll('spine itemref');
      for (const spineItem of spineItems) {
        const idref = spineItem.getAttribute('idref');
        const item = manifest[idref];
        if (!item) continue;
        if (item.mediaType !== 'application/xhtml+xml') continue;
        if ((item.properties || '').includes('nav')) continue;
        if ((item.href || '').toLowerCase().includes('nav.xhtml')) continue;

        const fullPath = resolveZipPath(opfBasePath, item.href);
        const xhtmlFile = zip.file(fullPath);
        if (!xhtmlFile) continue;

        const content = await xhtmlFile.async('text');
        const pageDoc = htmlParser.parseFromString(content, 'text/html');
        const heading = pageDoc.querySelector('h1, h2, h3, title');
        const title = heading?.textContent?.trim() || `Page ${pagesData.length + 1}`;

        pagesData.push({
          id: idref,
          href: item.href,
          content,
          title,
        });
      }

      setPages(pagesData);
      setCurrentPageIndex(0);
      setEpubData({
        zip,
        opfBasePath,
        cssText: cssParts.join('\n'),
      });
    } catch (parseError) {
      console.error('Error parsing EPUB:', parseError);
      setError('Failed to load this EPUB. Try another file.');
      setPages([]);
      setEpubData(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    const loadSource = async () => {
      if (epubFile) {
        await parseEpub(epubFile);
        return;
      }
      if (!epubUrl) {
        setIsLoading(false);
        return;
      }
      try {
        setIsLoading(true);
        const headers = {};
        if (token) {
          headers.Authorization = `Bearer ${token}`;
        }
        const response = await fetch(epubUrl, { headers });
        if (!response.ok) {
          throw new Error('Could not download EPUB');
        }
        const blob = await response.blob();
        await parseEpub(blob);
      } catch (loadError) {
        console.error('Error loading EPUB:', loadError);
        setError('Failed to load EPUB from your library.');
        setIsLoading(false);
      }
    };
    loadSource();
  }, [epubFile, epubUrl, token, parseEpub]);

  const handlePageChange = useCallback((pageIndex) => {
    if (pageIndex < 0 || pageIndex >= pages.length) return;
    setCurrentPageIndex(pageIndex);
  }, [pages.length]);

  const handleTocToggle = useCallback(() => {
    setIsTocOpen((prev) => !prev);
  }, []);

  if (error) {
    return (
      <ReaderContainer>
        <ContentArea>
          <CenteredState>
            <div>
              <i className="fas fa-exclamation-triangle" style={{ fontSize: '2.2rem', color: '#fca5a5' }}></i>
              <h3 style={{ margin: '0.9rem 0 0.4rem' }}>EPUB loading failed</h3>
              <p>{error}</p>
              {onBack && (
                <ActionButton type="button" onClick={onBack}>
                  Back to library
                </ActionButton>
              )}
            </div>
          </CenteredState>
        </ContentArea>
      </ReaderContainer>
    );
  }

  return (
    <ReaderContainer>
      {isLoading && (
        <CenteredState style={{ position: 'absolute', inset: 0, background: 'rgba(15, 23, 42, 0.45)', zIndex: 30 }}>
          <div>
            <i className="fas fa-spinner fa-spin" style={{ fontSize: '2rem', marginBottom: '0.8rem' }}></i>
            <div>Loading EPUB...</div>
          </div>
        </CenteredState>
      )}

      <Sidebar $isOpen={isTocOpen}>
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
          onBack={onBack}
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
