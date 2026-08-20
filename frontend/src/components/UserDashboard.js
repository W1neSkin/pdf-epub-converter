import React, { useCallback, useEffect, useMemo, useState } from 'react';
import styled from 'styled-components';
import { API_BASE_URL } from '../config';
import {
  ButtonRow,
  DangerAction,
  Panel,
  PrimaryAction,
  SecondaryAction,
} from './ui';

const DashboardContainer = styled.div`
  width: 100%;
  max-width: 1100px;
  margin: 0 auto;
`;

const HeaderBlock = styled.div`
  margin-bottom: 1.5rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
`;

const Title = styled.h2`
  font-size: 1.45rem;
  margin-bottom: 0.4rem;
`;

const Subtitle = styled.p`
  color: rgba(255, 255, 255, 0.78);
  line-height: 1.5;
`;

const StatsGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  margin-bottom: 1.25rem;
  overflow: hidden;

  @media (max-width: 620px) {
    grid-template-columns: 1fr;
  }
`;

const StatCard = styled(Panel)`
  border-radius: 0;
  border-right-width: 0;
  box-shadow: none;
  padding: 1.1rem 1.25rem;

  &:first-child {
    border-radius: 1rem 0 0 1rem;
  }

  &:last-child {
    border-right-width: 1px;
    border-radius: 0 1rem 1rem 0;
  }

  @media (max-width: 620px) {
    border-right-width: 1px;
    border-bottom-width: 0;
    border-radius: 0;

    &:first-child {
      border-radius: 1rem 1rem 0 0;
    }

    &:last-child {
      border-bottom-width: 1px;
      border-radius: 0 0 1rem 1rem;
    }
  }
`;

const StatValue = styled.div`
  font-size: 1.2rem;
  font-weight: 700;
  color: #f7c948;
`;

const StatLabel = styled.div`
  margin-top: 0.35rem;
  color: rgba(255, 255, 255, 0.78);
  font-size: 0.88rem;
`;

const LibraryPanel = styled(Panel)`
  padding: 0;
  overflow: hidden;
`;

const LibraryToolbar = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem 1.15rem;
  border-bottom: 1px solid #27324a;

  @media (max-width: 700px) {
    align-items: stretch;
    flex-direction: column;
  }
`;

const ToolbarControls = styled.div`
  display: flex;
  align-items: center;
  gap: 0.6rem;

  @media (max-width: 700px) {
    width: 100%;
  }
`;

const SearchInput = styled.input`
  width: min(340px, 42vw);
  border: 1px solid #34415c;
  border-radius: 0.7rem;
  background: #0d1526;
  color: white;
  padding: 0.7rem 0.85rem;

  @media (max-width: 700px) {
    width: 100%;
  }
`;

const ViewSwitch = styled.div`
  display: grid;
  grid-template-columns: 1fr 1fr;
  padding: 0.2rem;
  border: 1px solid #34415c;
  border-radius: 0.7rem;
  background: #0d1526;
`;

const ViewButton = styled.button`
  width: 2.35rem;
  height: 2.35rem;
  border: 0;
  border-radius: 0.5rem;
  background: ${(props) => (props.$active ? '#27324a' : 'transparent')};
  color: ${(props) => (props.$active ? '#f7c948' : 'rgba(255,255,255,0.55)')};
  cursor: pointer;
`;

const BooksGrid = styled.div`
  display: grid;
  grid-template-columns: ${(props) => (
    props.$view === 'grid'
      ? 'repeat(auto-fill, minmax(270px, 1fr))'
      : '1fr'
  )};
  gap: 0.75rem;
  padding: 1rem;
`;

const BookCard = styled(Panel).attrs({ as: 'article' })`
  display: grid;
  grid-template-columns: ${(props) => (
    props.$view === 'grid' ? '1fr' : '3.25rem minmax(0, 1fr) auto'
  )};
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  box-shadow: none;

  @media (max-width: 720px) {
    grid-template-columns: 2.8rem minmax(0, 1fr);
  }
`;

const BookIcon = styled.div`
  width: 3.25rem;
  height: 3.25rem;
  display: grid;
  place-items: center;
  border-radius: 0.8rem;
  background: rgba(247, 201, 72, 0.12);
  color: #f7c948;
  font-size: 1.15rem;

  @media (max-width: 720px) {
    width: 2.8rem;
    height: 2.8rem;
  }
`;

const BookContent = styled.div`
  min-width: 0;
`;

const BookName = styled.h3`
  font-size: 1.05rem;
  margin-bottom: 0.35rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
`;

const BookMeta = styled.div`
  color: rgba(255, 255, 255, 0.78);
  font-size: 0.85rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem 0.8rem;
`;

const Actions = styled(ButtonRow)`
  justify-content: flex-end;

  button {
    min-height: 2.4rem;
    padding: 0.4rem 0.75rem;
  }

  @media (max-width: 720px) {
    grid-column: 1 / -1;
    justify-content: stretch;

    button {
      flex: 1;
    }
  }
`;

const DeleteButton = styled(DangerAction)`
  width: 2.4rem;
  padding: 0;

  @media (max-width: 720px) {
    flex: 0 0 2.4rem !important;
  }
`;

const StateBox = styled.div`
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 0.85rem;
  background: rgba(255, 255, 255, 0.07);
  padding: 1.4rem;
  text-align: center;
  color: ${(props) => props.$error ? '#fecaca' : 'rgba(255, 255, 255, 0.82)'};
`;

const UserDashboard = ({
  user,
  onOpenBook,
  onNavigateToConvert,
  onOpenLocalEpub,
}) => {
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState(null);
  const [books, setBooks] = useState([]);
  const [search, setSearch] = useState('');
  const [viewMode, setViewMode] = useState('list');
  const [error, setError] = useState('');

  const token = user?.token || localStorage.getItem('authToken') || '';

  const loadDashboard = useCallback(async () => {
    if (!token) {
      setLoading(false);
      setError('Your session is unavailable. Please sign in again.');
      return;
    }
    setLoading(true);
    setError('');
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 15000);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const [statsResp, booksResp] = await Promise.all([
        fetch(`${API_BASE_URL}/library/stats`, { headers, signal: controller.signal }),
        fetch(`${API_BASE_URL}/library/books?limit=50`, { headers, signal: controller.signal }),
      ]);

      if (statsResp.ok) {
        const payload = await statsResp.json();
        setStats(payload.data || null);
      }
      if (booksResp.ok) {
        const payload = await booksResp.json();
        setBooks(payload.data || []);
      } else {
        setError('Could not load your books.');
      }
    } catch (loadError) {
      console.error(loadError);
      setError(
        loadError.name === 'AbortError'
          ? 'The library took too long to respond. Please retry.'
          : 'Failed to load dashboard data.'
      );
    } finally {
      clearTimeout(timeoutId);
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  const filteredBooks = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return books;
    return books.filter((book) => (
      (book.title || '').toLowerCase().includes(query) ||
      (book.original_filename || '').toLowerCase().includes(query)
    ));
  }, [books, search]);

  const formatFileSize = (bytes) => {
    if (!bytes) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB'];
    const step = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${(bytes / (1024 ** step)).toFixed(1)} ${units[step]}`;
  };

  const deleteBook = async (bookId) => {
    const shouldDelete = window.confirm('Delete this book from your library?');
    if (!shouldDelete) return;
    try {
      const response = await fetch(`${API_BASE_URL}/library/books/${bookId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        throw new Error('Delete failed');
      }
      setBooks((prev) => prev.filter((book) => book.id !== bookId));
      loadDashboard();
    } catch (deleteError) {
      console.error(deleteError);
      setError('Could not delete this book.');
    }
  };

  const downloadBook = async (book) => {
    try {
      const response = await fetch(`${API_BASE_URL}/library/books/${book.id}/file`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        throw new Error('Download failed');
      }
      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = objectUrl;
      link.download = `${book.title || 'book'}.epub`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(objectUrl);
    } catch (downloadError) {
      console.error(downloadError);
      setError('Could not download this book.');
    }
  };

  if (loading) {
    return (
      <StateBox>
        <i className="fas fa-spinner fa-spin" style={{ marginRight: '0.5rem' }}></i>
        Loading your library...
      </StateBox>
    );
  }

  return (
    <DashboardContainer>
      <HeaderBlock>
        <div>
          <Title>My Library</Title>
          <Subtitle>Read and manage EPUB books saved after conversion.</Subtitle>
        </div>
        <ButtonRow>
          <PrimaryAction type="button" onClick={onNavigateToConvert}>
            <i className="fas fa-plus" aria-hidden="true"></i>
            Convert PDF
          </PrimaryAction>
          <SecondaryAction type="button" onClick={onOpenLocalEpub}>
            Open EPUB from device
          </SecondaryAction>
        </ButtonRow>
      </HeaderBlock>

      {stats && Number(stats.total_books || 0) > 0 && (
        <StatsGrid>
          <StatCard>
            <StatValue>{stats.total_books || 0}</StatValue>
            <StatLabel>Books</StatLabel>
          </StatCard>
          <StatCard>
            <StatValue>{formatFileSize(stats.total_size || 0)}</StatValue>
            <StatLabel>Storage</StatLabel>
          </StatCard>
          <StatCard>
            <StatValue>{stats.total_pages || 0}</StatValue>
            <StatLabel>Total pages</StatLabel>
          </StatCard>
        </StatsGrid>
      )}

      {!error && (books.length === 0 ? (
        <StateBox>
          <div>No EPUB books yet.</div>
          <Actions style={{ justifyContent: 'center' }}>
            <PrimaryAction type="button" onClick={onNavigateToConvert}>
              Convert your first PDF
            </PrimaryAction>
            <SecondaryAction type="button" onClick={onOpenLocalEpub}>
              Open an EPUB file
            </SecondaryAction>
          </Actions>
        </StateBox>
      ) : (
        <LibraryPanel>
          <LibraryToolbar>
            <div>
              <strong>Books</strong>
              <div style={{ color: 'rgba(255,255,255,0.58)', fontSize: '0.82rem', marginTop: '0.2rem' }}>
                {filteredBooks.length} of {books.length}
              </div>
            </div>
            <ToolbarControls>
              <SearchInput
                type="text"
                placeholder="Search title or file..."
                aria-label="Search books"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
              <ViewSwitch aria-label="Library view">
                <ViewButton
                  type="button"
                  $active={viewMode === 'list'}
                  aria-label="List view"
                  aria-pressed={viewMode === 'list'}
                  onClick={() => setViewMode('list')}
                >
                  <i className="fas fa-list" aria-hidden="true"></i>
                </ViewButton>
                <ViewButton
                  type="button"
                  $active={viewMode === 'grid'}
                  aria-label="Grid view"
                  aria-pressed={viewMode === 'grid'}
                  onClick={() => setViewMode('grid')}
                >
                  <i className="fas fa-grip" aria-hidden="true"></i>
                </ViewButton>
              </ViewSwitch>
            </ToolbarControls>
          </LibraryToolbar>
          {filteredBooks.length === 0 ? (
            <StateBox style={{ margin: '1rem' }}>No books match this search.</StateBox>
          ) : (
            <BooksGrid $view={viewMode}>
              {filteredBooks.map((book) => (
                <BookCard key={book.id} $view={viewMode}>
                  <BookIcon>
                    <i className="fas fa-book-open" aria-hidden="true"></i>
                  </BookIcon>
                  <BookContent>
                    <BookName title={book.title || book.original_filename}>
                      {book.title || book.original_filename || 'Untitled book'}
                    </BookName>
                    <BookMeta>
                      <span>{book.pages || 0} pages</span>
                      <span>{formatFileSize(book.file_size)}</span>
                      {book.original_filename && book.original_filename !== book.title && (
                        <span title={book.original_filename}>{book.original_filename}</span>
                      )}
                    </BookMeta>
                  </BookContent>
                  <Actions>
                    <PrimaryAction type="button" onClick={() => onOpenBook && onOpenBook(book)}>
                      Read
                    </PrimaryAction>
                    <SecondaryAction type="button" onClick={() => downloadBook(book)}>
                      Download
                    </SecondaryAction>
                    <DeleteButton
                      type="button"
                      aria-label={`Delete ${book.title || 'book'}`}
                      title="Delete book"
                      onClick={() => deleteBook(book.id)}
                    >
                      <i className="fas fa-trash" aria-hidden="true"></i>
                    </DeleteButton>
                  </Actions>
                </BookCard>
              ))}
            </BooksGrid>
          )}
        </LibraryPanel>
      ))}

      {error && (
        <StateBox $error>
          <div>{error}</div>
          <Actions style={{ justifyContent: 'center', marginTop: '0.75rem' }}>
            <SecondaryAction type="button" onClick={loadDashboard}>
              Retry
            </SecondaryAction>
          </Actions>
        </StateBox>
      )}
    </DashboardContainer>
  );
};

export default UserDashboard;
