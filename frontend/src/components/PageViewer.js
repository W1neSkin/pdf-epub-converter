import React, { useCallback, useEffect, useRef, useState } from 'react';
import styled from 'styled-components';

const ViewerContainer = styled.div`
  width: 100%;
  height: 100%;
  overflow: auto;
  background: #ffffff;
`;

const PageContent = styled.div`
  width: ${(props) => (
    props.$fixedLayout && props.$pageWidth
      ? `${props.$pageWidth * props.$pageScale}px`
      : 'auto'
  )};
  height: ${(props) => (
    props.$fixedLayout && props.$pageHeight
      ? `${props.$pageHeight * props.$pageScale}px`
      : 'auto'
  )};
  max-width: ${(props) => (props.$fixedLayout ? 'none' : '900px')};
  margin: 0 auto;
  padding: ${(props) => (props.$fixedLayout ? '0' : '1.25rem')};
  color: #111827;
  line-height: 1.7;
  min-height: ${(props) => (props.$fixedLayout ? '0' : '100%')};

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

  .fixed-layout-page {
    position: relative;
    margin: 0;
    transform: scale(${(props) => props.$pageScale});
    transform-origin: top left;
  }

  .fixed-layout-page .fixed-layout-figure {
    margin: 0;
    width: 100%;
    height: 100%;
  }

  .fixed-layout-page .page-image {
    display: block;
    width: 100%;
    height: 100%;
  }

  .fixed-layout-page .text-overlay {
    position: absolute;
    left: 0;
    top: 0;
    width: 100%;
    height: 100%;
  }

  ::selection {
    background: rgba(59, 130, 246, 0.25);
  }
`;

export function calculatePageScale(availableWidth, pageWidth) {
  if (!availableWidth || !pageWidth || availableWidth <= 0 || pageWidth <= 0) {
    return 1;
  }
  return Math.min(1, availableWidth / pageWidth);
}

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
  const [isFixedLayout, setIsFixedLayout] = useState(false);
  const [fixedPageSize, setFixedPageSize] = useState({ width: 0, height: 0 });
  const [availableWidth, setAvailableWidth] = useState(0);
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
      const fixedPage = bodyNode.querySelector('.fixed-layout-page');
      const fixedLayoutDetected = Boolean(fixedPage);
      setIsFixedLayout(fixedLayoutDetected);
      setFixedPageSize(
        fixedPage
          ? {
              width: Number.parseFloat(fixedPage.style.width) || 0,
              height: Number.parseFloat(fixedPage.style.height) || 0,
            }
          : { width: 0, height: 0 }
      );

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
      setIsFixedLayout(false);
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

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return undefined;

    const updateWidth = () => setAvailableWidth(Math.max(0, container.clientWidth - 2));
    updateWidth();

    if (typeof ResizeObserver === 'undefined') {
      window.addEventListener('resize', updateWidth);
      return () => window.removeEventListener('resize', updateWidth);
    }

    const observer = new ResizeObserver(updateWidth);
    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  const pageScale = isFixedLayout
    ? calculatePageScale(availableWidth, fixedPageSize.width)
    : 1;

  if (!pages || pages.length === 0) {
    return (
      <ViewerContainer ref={containerRef}>
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
      <PageContent
        $fixedLayout={isFixedLayout}
        $pageWidth={fixedPageSize.width}
        $pageHeight={fixedPageSize.height}
        $pageScale={pageScale}
        data-page-scale={pageScale}
        dangerouslySetInnerHTML={{ __html: processedContent }}
      />
    </ViewerContainer>
  );
};

export default PageViewer;
