import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import UserDashboard from './UserDashboard';


test('offers conversion and local EPUB actions in an empty library', async () => {
  global.fetch = jest.fn((url) => {
    const requestUrl = String(url);
    if (requestUrl.includes('/library/stats')) {
      return Promise.resolve({
        ok: true,
        json: async () => ({
          data: {
            total_books: 0,
            total_pages: 0,
            total_size: 0,
          },
        }),
      });
    }
    return Promise.resolve({
      ok: true,
      json: async () => ({ data: [] }),
    });
  });

  const onNavigateToConvert = jest.fn();
  const onOpenLocalEpub = jest.fn();
  render(
    <UserDashboard
      user={{ token: 'token' }}
      onNavigateToConvert={onNavigateToConvert}
      onOpenLocalEpub={onOpenLocalEpub}
    />
  );

  expect(await screen.findByText(/No EPUB books yet/i)).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: /^Convert PDF$/i }));
  fireEvent.click(screen.getByRole('button', { name: /^Open EPUB from device$/i }));

  expect(onNavigateToConvert).toHaveBeenCalledTimes(1);
  expect(onOpenLocalEpub).toHaveBeenCalledTimes(1);
});

test('uses list view by default and lets the user switch views', async () => {
  global.fetch = jest.fn((url) => {
    const requestUrl = String(url);
    if (requestUrl.includes('/library/stats')) {
      return Promise.resolve({
        ok: true,
        json: async () => ({
          data: { total_books: 1, total_pages: 10, total_size: 1024 },
        }),
      });
    }
    return Promise.resolve({
      ok: true,
      json: async () => ({
        data: [{
          id: 'book-1',
          title: 'Credit report',
          original_filename: 'credit-report.pdf',
          pages: 10,
          file_size: 1024,
        }],
      }),
    });
  });

  render(<UserDashboard user={{ token: 'token' }} />);

  expect(await screen.findByText('Credit report')).toBeInTheDocument();
  const listButton = screen.getByRole('button', { name: /List view/i });
  const gridButton = screen.getByRole('button', { name: /Grid view/i });
  expect(listButton).toHaveAttribute('aria-pressed', 'true');

  fireEvent.click(gridButton);
  expect(gridButton).toHaveAttribute('aria-pressed', 'true');
  expect(listButton).toHaveAttribute('aria-pressed', 'false');

  fireEvent.change(screen.getByRole('textbox', { name: /Search books/i }), {
    target: { value: 'missing title' },
  });
  expect(screen.getByText(/No books match this search/i)).toBeInTheDocument();
  expect(screen.getByRole('textbox', { name: /Search books/i })).toBeInTheDocument();
});
