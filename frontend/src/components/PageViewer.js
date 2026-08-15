import React, { useCallback, useEffect, useRef, useState } from 'react';
import styled from 'styled-components';

const ViewerContainer = styled.div`
  width: 100%;
  height: 100%;
  overflow: auto;
  background: #ffffff;
`;

const PageContent = styled.div`
  max-width: 900px;
  margin: 0 auto;
  padding: 1.25rem;
  color: #111827;
  line-height: 1.7;
  min-height: 100%;

  .page-title {
    margin: 0 0 1rem;
    font-size: 1.1rem;
    color: #374151;
  }

  p {
    margin: 0 0 0.8rem;
  }

  img {
    max-width: 100%;
    height: auto;
  }

  ::selection {
    background: rgba(59, 130, 246, 0.25);
  }
`;

function resolveZipPath(opfBasePath, pageHref, assetHref) {
  const cleanAsset = (assetHref || '').split('#')[0].split('?')[0];
  if (!cleanAsset) {
    return '';
  }
  const pageFullPath = `${opfBasePath || ''}${pageHref || ''}`;
  const pageDir = pageFullPath.includes('/')
    ? pageFullPath.slice(0, pageFullPath.lastIndexOf('/') + 1)
    : '';
  const combined = `${pageDir}${cleanAsset}`;
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

const PageViewer = ({ pages, currentPageIndex, epubData }) => {
  const [processedContent, setProcessedContent] = useState('');
  const containerRef = useRef(null);
  const objectUrlsRef = useRef([]);

  const cleanupObjectUrls = useCallback(() => {
    objectUrlsRef.current.forEach((url) => URL.revokeObjectURL(url));
    objectUrlsRef.current = [];
  }, []);

  const processPageContent = useCallback(async (page) => {
    if (!page || !page.content) {
      setProcessedContent('<div>No content available</div>');
      return;
    }

    cleanupObjectUrls();

    try {
      const parser = new DOMParser();
      const doc = parser.parseFromString(page.content, 'text/html');
      const bodyNode = doc.body || doc.documentElement;

      if (epubData && epubData.zip) {
        const images = bodyNode.querySelectorAll('img');
        for (const img of images) {
          const src = img.getAttribute('src');
          if (!src || src.startsWith('http') || src.startsWith('data:')) {
            continue;
          }
          const zipPath = resolveZipPath(epubData.opfBasePath, page.href, src);
          if (!zipPath) {
            continue;
          }
          const imageFile = epubData.zip.file(zipPath);
          if (!imageFile) {
            continue;
          }
          const imageBlob = await imageFile.async('blob');
          const objectUrl = URL.createObjectURL(imageBlob);
          objectUrlsRef.current.push(objectUrl);
          img.setAttribute('src', objectUrl);
        }
      }

      const cssBlock = epubData?.cssText
        ? `<style>${epubData.cssText}</style>`
        : '';
      setProcessedContent(`${cssBlock}${bodyNode.innerHTML}`);

      if (containerRef.current) {
        containerRef.current.scrollTop = 0;
      }
    } catch (error) {
      console.error('Error processing page content:', error);
      setProcessedContent('<div>Error loading page content</div>');
    }
  }, [cleanupObjectUrls, epubData]);

  useEffect(() => {
    if (pages && pages[currentPageIndex]) {
      processPageContent(pages[currentPageIndex]);
    }
  }, [pages, currentPageIndex, processPageContent]);

  useEffect(() => {
    return () => cleanupObjectUrls();
  }, [cleanupObjectUrls]);

  if (!pages || pages.length === 0) {
    return (
      <ViewerContainer>
        <PageContent>
          <div style={{ textAlign: 'center', padding: '2rem', color: '#6b7280' }}>
            No pages to display
          </div>
        </PageContent>
      </ViewerContainer>
    );
  }

  return (
    <ViewerContainer ref={containerRef}>
      <PageContent dangerouslySetInnerHTML={{ __html: processedContent }} />
    </ViewerContainer>
  );
};

export default PageViewer;
