import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import ReaderControls from './ReaderControls';


test('keeps essential reader actions accessible', () => {
  const onBack = jest.fn();
  const onTocToggle = jest.fn();
  const onPageChange = jest.fn();

  render(
    <ReaderControls
      currentPageIndex={1}
      totalPages={3}
      onPageChange={onPageChange}
      onTocToggle={onTocToggle}
      isTocOpen={false}
      bookTitle="Example book"
      onBack={onBack}
    />
  );

  expect(screen.getByText('Example book')).toBeInTheDocument();
  expect(screen.getByText(/Page 2 of 3/i)).toBeInTheDocument();

  fireEvent.click(screen.getByRole('button', { name: /Back to library/i }));
  fireEvent.click(screen.getByRole('button', { name: /Toggle pages/i }));
  fireEvent.click(screen.getByRole('button', { name: /Previous page/i }));
  fireEvent.click(screen.getByRole('button', { name: /Next page/i }));

  expect(onBack).toHaveBeenCalledTimes(1);
  expect(onTocToggle).toHaveBeenCalledTimes(1);
  expect(onPageChange).toHaveBeenNthCalledWith(1, 0);
  expect(onPageChange).toHaveBeenNthCalledWith(2, 2);
});
