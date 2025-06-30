import React from 'react';
import styled from 'styled-components';

const ControlsContainer = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.5rem;
  background: rgba(0, 0, 0, 0.2);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  color: white;
`;

const LeftControls = styled.div`
  display: flex;
  align-items: center;
  gap: 1rem;
`;

const CenterInfo = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  flex: 1;
  max-width: 400px;
  margin: 0 2rem;
`;

const BookTitle = styled.h2`
  font-size: 1.1rem;
  font-weight: 500;
  margin-bottom: 0.3rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
`;

const PageInfo = styled.div`
  font-size: 0.9rem;
  color: rgba(255, 255, 255, 0.7);
  display: flex;
  align-items: center;
  gap: 1rem;
`;

const ProgressBar = styled.div`
  width: 100px;
  height: 4px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 2px;
  overflow: hidden;
`;

const ProgressFill = styled.div`
  width: ${props => props.progress}%;
  height: 100%;
  background: #ffd700;
  transition: width 0.3s ease;
`;

const RightControls = styled.div`
  display: flex;
  align-items: center;
  gap: 0.5rem;
`;

const ControlButton = styled.button`
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: white;
  padding: 0.5rem;
  border-radius: 0.3rem;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;

  &:hover:not(:disabled) {
    background: rgba(255, 255, 255, 0.2);
    border-color: rgba(255, 255, 255, 0.3);
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  i {
    font-size: 1rem;
  }
`;

const TocButton = styled(ControlButton)`
  background: ${props => props.isActive ? 'rgba(255, 215, 0, 0.3)' : 'rgba(255, 255, 255, 0.1)'};
  border-color: ${props => props.isActive ? '#ffd700' : 'rgba(255, 255, 255, 0.2)'};
`;

const NavigationControls = styled.div`
  display: flex;
  align-items: center;
  gap: 0.5rem;
`;

const ReaderControls = ({ 
  currentPageIndex, 
  totalPages, 
  onPageChange, 
  onTocToggle, 
  isTocOpen, 
  bookTitle 
}) => {
  const progress = totalPages > 0 ? ((currentPageIndex + 1) / totalPages) * 100 : 0;

  const handlePreviousPage = () => {
    if (currentPageIndex > 0) {
      onPageChange(currentPageIndex - 1);
    }
  };

  const handleNextPage = () => {
    if (currentPageIndex < totalPages - 1) {
      onPageChange(currentPageIndex + 1);
    }
  };

  return (
    <ControlsContainer>
      <LeftControls>
        <TocButton onClick={onTocToggle} isActive={isTocOpen} title="Toggle Table of Contents">
          <i className="fas fa-list"></i>
        </TocButton>
      </LeftControls>

      <CenterInfo>
        <BookTitle title={bookTitle}>{bookTitle || 'EPUB Reader'}</BookTitle>
        <PageInfo>
          <span>Page {currentPageIndex + 1} of {totalPages}</span>
          <ProgressBar>
            <ProgressFill progress={progress} />
          </ProgressBar>
          <span>{Math.round(progress)}%</span>
        </PageInfo>
      </CenterInfo>

      <RightControls>
        <NavigationControls>
          <ControlButton 
            onClick={handlePreviousPage}
            disabled={currentPageIndex === 0}
            title="Previous Page"
          >
            <i className="fas fa-chevron-left"></i>
          </ControlButton>
          
          <ControlButton 
            onClick={handleNextPage}
            disabled={currentPageIndex >= totalPages - 1}
            title="Next Page"
          >
            <i className="fas fa-chevron-right"></i>
          </ControlButton>
        </NavigationControls>
      </RightControls>
    </ControlsContainer>
  );
};

export default ReaderControls; 