import React from 'react';
import { render, waitFor } from '@testing-library/react';
import PageViewer, { calculatePageScale } from './PageViewer';


describe('calculatePageScale', () => {
  test('shrinks a fixed-layout page to fit the viewer width', () => {
    expect(calculatePageScale(900, 1240)).toBeCloseTo(0.726, 3);
  });

  test('does not enlarge pages that already fit', () => {
    expect(calculatePageScale(1240, 900)).toBe(1);
  });
});


describe('PageViewer fixed-layout sizing', () => {
  const originalClientWidth = Object.getOwnPropertyDescriptor(
    HTMLElement.prototype,
    'clientWidth'
  );
  const originalResizeObserver = global.ResizeObserver;

  beforeEach(() => {
    Object.defineProperty(HTMLElement.prototype, 'clientWidth', {
      configurable: true,
      get: () => 620,
    });
    global.ResizeObserver = class {
      observe() {}
      disconnect() {}
    };
  });

  afterEach(() => {
    if (originalClientWidth) {
      Object.defineProperty(HTMLElement.prototype, 'clientWidth', originalClientWidth);
    }
    global.ResizeObserver = originalResizeObserver;
  });

  test('measures the viewer before EPUB pages finish loading', async () => {
    const page = {
      href: 'page_001.xhtml',
      content: `
        <html>
          <body>
            <article class="pdf-page fixed-layout-page" style="width:1240px;height:1755px;">
              <img class="page-image" src="data:image/png;base64,test" alt="Page 1" />
            </article>
          </body>
        </html>
      `,
    };
    const { container, rerender } = render(
      <PageViewer pages={[]} currentPageIndex={0} epubData={null} />
    );

    rerender(
      <PageViewer pages={[page]} currentPageIndex={0} epubData={null} />
    );

    await waitFor(() => {
      const pageContent = container.querySelector('[data-page-scale]');
      expect(Number(pageContent.getAttribute('data-page-scale'))).toBeCloseTo(
        618 / 1240,
        3
      );
    });
  });
});
