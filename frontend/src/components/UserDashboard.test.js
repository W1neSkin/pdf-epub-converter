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
