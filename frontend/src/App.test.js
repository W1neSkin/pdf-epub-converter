import { render, screen } from '@testing-library/react';
import App from './App';

beforeEach(() => {
  localStorage.clear();
  if (global.fetch) {
    global.fetch.mockReset?.();
  }
});

test('renders app title', () => {
  render(<App />);
  expect(screen.getAllByText(/PDF to EPUB Converter/i).length).toBeGreaterThan(0);
});

test('shows persistent navigation for authenticated user', async () => {
  localStorage.setItem('authToken', 'token');
  localStorage.setItem('userData', JSON.stringify({
    token: 'token',
    email: 'reader@example.com',
    user_id: 'user-1',
  }));

  global.fetch = jest.fn((url) => {
    const requestUrl = String(url);
    if (requestUrl.includes('/auth/verify')) {
      return Promise.resolve({ ok: true, status: 200 });
    }
    if (requestUrl.includes('/library/stats')) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => ({ data: { total_books: 0, total_size: 0, total_pages: 0, recent_conversions: 0 } }),
      });
    }
    if (requestUrl.includes('/library/books')) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => ({ data: [] }),
      });
    }
    return Promise.resolve({ ok: true, status: 200, json: async () => ({}) });
  });
  render(<App />);

  expect(await screen.findByRole('button', { name: /Library/i })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Convert PDF/i })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Read EPUB/i })).toBeInTheDocument();

  localStorage.removeItem('authToken');
  localStorage.removeItem('userData');
});
