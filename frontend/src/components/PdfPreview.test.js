import React from 'react';
import { render, screen } from '@testing-library/react';
import PdfPreview from './PdfPreview';


test('shows a local PDF preview without uploading the file', () => {
  const originalCreateObjectUrl = URL.createObjectURL;
  const originalRevokeObjectUrl = URL.revokeObjectURL;
  URL.createObjectURL = jest.fn(() => 'blob:local-preview');
  URL.revokeObjectURL = jest.fn();

  const file = new File(['pdf'], 'report.pdf', { type: 'application/pdf' });
  const { unmount } = render(<PdfPreview file={file} />);

  expect(screen.getByTitle('PDF preview')).toHaveAttribute(
    'src',
    'blob:local-preview#page=1&view=FitH&navpanes=0'
  );
  expect(screen.getByRole('link', { name: /Open full preview/i })).toHaveAttribute(
    'href',
    'blob:local-preview'
  );

  unmount();
  expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:local-preview');
  URL.createObjectURL = originalCreateObjectUrl;
  URL.revokeObjectURL = originalRevokeObjectUrl;
});
