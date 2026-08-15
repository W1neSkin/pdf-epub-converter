import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import PdfUploader from './PdfUploader';
import { getPdfInfo } from '../pdfInfo';

jest.mock('../pdfInfo', () => ({
  getPdfInfo: jest.fn(),
}));

const user = { token: 'test-token' };

describe('PdfUploader', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('sends one convert request per selected PDF', async () => {
    getPdfInfo.mockResolvedValue({
      name: 'sample.pdf',
      pages: 1,
      sizeMb: 0.1,
      title: '',
    });

    global.fetch = jest.fn((url) => {
      const requestUrl = String(url);
      if (requestUrl.includes('/api/convert')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ success: true, conversion_id: 'id-1' }),
        });
      }
      if (requestUrl.includes('/api/status/')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            status: 'completed',
            progress: 100,
            message: 'done',
            download_url: '/api/download/id-1',
          }),
        });
      }
      return Promise.resolve({ ok: true, json: async () => ({}) });
    });

    const { container } = render(<PdfUploader user={user} onEpubGenerated={jest.fn()} onBack={jest.fn()} />);
    const input = container.querySelector('input[type="file"]');
    const file = new File(['pdf'], 'sample.pdf', { type: 'application/pdf' });

    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText(/EPUB generated successfully/i)).toBeInTheDocument();
    });

    const convertCalls = global.fetch.mock.calls.filter(([url]) => String(url).includes('/api/convert'));
    expect(convertCalls).toHaveLength(1);
  });

  test('allows user to cancel while converter is starting', async () => {
    getPdfInfo.mockResolvedValue({
      name: 'sample.pdf',
      pages: 1,
      sizeMb: 0.1,
      title: '',
    });

    global.fetch = jest.fn((url, options = {}) => {
      const requestUrl = String(url);
      if (requestUrl.includes('/api/convert')) {
        return new Promise((resolve, reject) => {
          if (options.signal) {
            options.signal.addEventListener('abort', () => {
              const err = new Error('aborted');
              err.name = 'AbortError';
              reject(err);
            });
          }
        });
      }
      return Promise.resolve({ ok: true, json: async () => ({}) });
    });

    const { container } = render(<PdfUploader user={user} onEpubGenerated={jest.fn()} onBack={jest.fn()} />);
    const input = container.querySelector('input[type="file"]');
    const file = new File(['pdf'], 'sample.pdf', { type: 'application/pdf' });

    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText(/Uploading PDF/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /Cancel/i }));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Choose PDF/i })).toBeInTheDocument();
    });

    const convertCalls = global.fetch.mock.calls.filter(([url]) => String(url).includes('/api/convert'));
    expect(convertCalls).toHaveLength(1);
  });

  test('extracts tables in CSV mode with dedicated endpoint', async () => {
    getPdfInfo.mockResolvedValue({
      name: 'sample.pdf',
      pages: 1,
      sizeMb: 0.1,
      title: '',
    });

    global.fetch = jest.fn((url) => {
      const requestUrl = String(url);
      if (requestUrl.includes('/api/extract-tables')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ success: true, conversion_id: 'csv-1' }),
        });
      }
      if (requestUrl.includes('/api/status/')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            status: 'completed',
            progress: 100,
            message: 'done',
            download_url: '/api/download/csv-1',
            output_kind: 'csv',
            download_name: 'sample_tables.csv',
          }),
        });
      }
      return Promise.resolve({ ok: true, json: async () => ({}) });
    });

    const { container } = render(<PdfUploader user={user} onEpubGenerated={jest.fn()} onBack={jest.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: /Extract tables \(CSV\)/i }));

    const input = container.querySelector('input[type="file"]');
    const file = new File(['pdf'], 'sample.pdf', { type: 'application/pdf' });
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText(/CSV generated successfully/i)).toBeInTheDocument();
    });

    const csvCalls = global.fetch.mock.calls.filter(([url]) => String(url).includes('/api/extract-tables'));
    expect(csvCalls).toHaveLength(1);
  });

  test('handles expired token and requests re-login', async () => {
    getPdfInfo.mockResolvedValue({
      name: 'sample.pdf',
      pages: 1,
      sizeMb: 0.1,
      title: '',
    });

    global.fetch = jest.fn((url) => {
      const requestUrl = String(url);
      if (requestUrl.includes('/api/convert')) {
        return Promise.resolve({
          ok: false,
          status: 401,
          json: async () => ({ message: 'Token has expired' }),
        });
      }
      return Promise.resolve({ ok: true, json: async () => ({}) });
    });

    const onSessionExpired = jest.fn();
    const { container } = render(
      <PdfUploader
        user={user}
        onSessionExpired={onSessionExpired}
        onEpubGenerated={jest.fn()}
        onBack={jest.fn()}
      />
    );
    const input = container.querySelector('input[type="file"]');
    const file = new File(['pdf'], 'sample.pdf', { type: 'application/pdf' });
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(onSessionExpired).toHaveBeenCalledTimes(1);
    });

    expect(screen.getByText(/Session expired\. Please log in again\./i)).toBeInTheDocument();
  });
});
