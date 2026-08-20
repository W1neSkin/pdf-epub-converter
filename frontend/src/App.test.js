import { fireEvent, render, screen, within } from '@testing-library/react';
import App from './App';

beforeEach(() => {
  localStorage.clear();
  if (global.fetch) {
    global.fetch.mockReset?.();
  }
});

test('renders app title', () => {
  render(<App />);
  expect(screen.getAllByText(/PDF Converter|PDF to EPUB/i).length).toBeGreaterThan(0);
});

test('opens Convert after signing in from the landing page', async () => {
  global.fetch = jest.fn().mockResolvedValue({
    ok: true,
    status: 200,
    text: async () => JSON.stringify({
      success: true,
      data: {
        access_token: 'token',
        user_id: 'user-1',
      },
    }),
  });

  render(<App />);
  fireEvent.click(await screen.findByRole('button', { name: /Start converting/i }));

  const dialog = screen.getByRole('dialog', { name: /Authentication/i });
  expect(
    within(dialog).getByRole('button', { name: /Close authentication dialog/i })
  ).toHaveFocus();
  fireEvent.change(within(dialog).getByLabelText(/Email/i), {
    target: { value: 'reader@example.com' },
  });
  fireEvent.change(within(dialog).getByLabelText(/Password/i), {
    target: { value: 'password123' },
  });
  fireEvent.click(within(dialog).getByRole('button', { name: /^Sign in$/i }));

  expect(await screen.findByText(/Convert or export PDF/i)).toBeInTheDocument();
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

  const navigation = await screen.findByRole('navigation', { name: /Main navigation/i });
  expect(within(navigation).getByRole('button', { name: /^Library$/i })).toBeInTheDocument();
  expect(within(navigation).getByRole('button', { name: /^Convert$/i })).toBeInTheDocument();
  expect(within(navigation).queryByRole('button', { name: /Read EPUB/i })).not.toBeInTheDocument();

  localStorage.removeItem('authToken');
  localStorage.removeItem('userData');
});
