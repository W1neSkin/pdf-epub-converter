import React from 'react';
import styled from 'styled-components';

const TocContainer = styled.div`
  height: 100%;
  display: flex;
  flex-direction: column;
  color: white;
`;

const TocHeader = styled.div`
  padding: 1.5rem 1rem 1rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
`;

const BookTitle = styled.h3`
  font-size: 1.1rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
  line-height: 1.3;
  word-wrap: break-word;
`;

const BookAuthor = styled.p`
  font-size: 0.9rem;
  color: rgba(255, 255, 255, 0.7);
  margin-bottom: 0.5rem;
`;

const PageCount = styled.p`
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.5);
`;

const TocContent = styled.div`
  flex: 1;
  overflow-y: auto;
  padding: 1rem 0;

  &::-webkit-scrollbar {
    width: 6px;
  }

  &::-webkit-scrollbar-track {
    background: rgba(255, 255, 255, 0.1);
  }

  &::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.3);
    border-radius: 3px;
  }

  &::-webkit-scrollbar-thumb:hover {
    background: rgba(255, 255, 255, 0.5);
  }
`;

const PageItem = styled.div`
  padding: 0.8rem 1rem;
  cursor: pointer;
  transition: all 0.2s ease;
  border-left: 3px solid transparent;
  background: ${props => props.isActive ? 'rgba(255, 215, 0, 0.2)' : 'transparent'};
  border-left-color: ${props => props.isActive ? '#ffd700' : 'transparent'};

  &:hover {
    background: rgba(255, 255, 255, 0.1);
    border-left-color: rgba(255, 255, 255, 0.3);
  }
`;

const PageNumber = styled.span`
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.6);
  margin-right: 0.5rem;
  font-weight: 500;
`;

const PageTitle = styled.span`
  font-size: 0.9rem;
  line-height: 1.4;
  display: block;
  margin-top: 0.2rem;
`;

const TableOfContents = ({ pages, currentPageIndex, onPageSelect, bookMetadata }) => {
  return (
    <TocContainer>
      <TocHeader>
        <BookTitle>{bookMetadata.title || 'Unknown Title'}</BookTitle>
        <BookAuthor>{bookMetadata.creator || 'Unknown Author'}</BookAuthor>
        <PageCount>{pages.length} pages</PageCount>
      </TocHeader>
      
      <TocContent>
        {pages.map((page, index) => (
          <PageItem
            key={page.id || index}
            isActive={currentPageIndex === index}
            onClick={() => onPageSelect(index)}
          >
            <PageNumber>Page {index + 1}</PageNumber>
            <PageTitle>{page.title}</PageTitle>
          </PageItem>
        ))}
      </TocContent>
    </TocContainer>
  );
};

export default TableOfContents; 