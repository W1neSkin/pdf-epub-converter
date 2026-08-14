import { render, screen } from '@testing-library/react';
import App from './App';

test('renders app title', () => {
  render(<App />);
  expect(screen.getAllByText(/PDF to EPUB Converter/i).length).toBeGreaterThan(0);
});
