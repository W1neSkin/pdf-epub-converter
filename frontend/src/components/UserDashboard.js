import React, { useCallback, useEffect, useMemo, useState } from 'react';
import styled from 'styled-components';
import { API_BASE_URL } from '../config';

const DashboardContainer = styled.div`
  width: 100%;
`;

const HeaderBlock = styled.div`
  margin-bottom: 1.25rem;
`;

const Title = styled.h2`
  font-size: 1.55rem;
  margin-bottom: 0.4rem;
`;

const Subtitle = styled.p`
  color: rgba(255, 255, 255, 0.78);
  line-height: 1.5;
`;

const StatsGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 0.85rem;
  margin: 1rem 0 1.5rem;
`;

const StatCard = styled.div`
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 0.85rem;
  padding: 1rem;
`;

const StatValue = styled.div`
  font-size: 1.35rem;
  font-weight: 700;
  color: #facc15;
`;

const StatLabel = styled.div`
  margin-top: 0.35rem;
  color: rgba(255, 255, 255, 0.78);
  font-size: 0.88rem;
`;

const SearchInput = styled.input`
  width: 100%;
  max-width: 460px;
  border: 1px solid rgba(255, 255, 255, 0.25);
  border-radius: 0.6rem;
  background: rgba(255, 255, 255, 0.08);
  color: white;
  padding: 0.7rem 0.9rem;
  margin-bottom: 1rem;
`;

const BooksGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 0.9rem;
`;

const BookCard = styled.article`
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 0.8rem;
  padding: 0.95rem;
`;

const BookName = styled.h3`
  font-size: 1.05rem;
  margin-bottom: 0.6rem;
  word-break: break-word;
`;

const BookMeta = styled.div`
  color: rgba(255, 255, 255, 0.78);
  font-size: 0.85rem;
  line-height: 1.45;
`;

const Actions = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
  margin-top: 0.85rem;
`;

const Button = styled.button`
  min-height: 2.4rem;
  border-radius: 0.55rem;
  border: 1px solid ${(props) => (props.$danger ? 'rgba(248, 113, 113, 0.75)' : 'rgba(255, 255, 255, 0.26)')};
  background: ${(props) => (props.$danger ? 'rgba(248, 113, 113, 0.14)' : 'rgba(255, 255, 255, 0.1)')};
  color: ${(props) => (props.$danger ? '#fecaca' : 'white')};
  padding: 0.45rem 0.7rem;
  cursor: pointer;
  font-weight: 600;
`;

const StateBox = styled.div`
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 0.85rem;
  background: rgba(255, 255, 255, 0.07);
  padding: 1.4rem;
  text-align: center;
  color: ${(props) => props.$error ? '#fecaca' : 'rgba(255, 255, 255, 0.82)'};
`;

const UserDashboard = ({ user, onOpenBook }) => {
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState(null);
  const [books, setBooks] = useState([]);
  const [search, setSearch] = useState('');
  const [error, setError] = useState('');

  const token = user?.token || localStorage.getItem('authToken') || '';

  const loadDashboard = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError('');
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const [statsResp, booksResp] = await Promise.all([
        fetch(`${API_BASE_URL}/library/stats`, { headers }),
        fetch(`${API_BASE_URL}/library/books?limit=50`, { headers }),
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
      setError('Failed to load dashboard data.');
    } finally {
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
        <Title>My Library</Title>
        <Subtitle>Open converted books, download EPUB files, and manage your collection.</Subtitle>
      </HeaderBlock>

      {stats && (
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
          <StatCard>
            <StatValue>{stats.recent_conversions || 0}</StatValue>
            <StatLabel>Recent conversions</StatLabel>
          </StatCard>
        </StatsGrid>
      )}

      {books.length > 0 && (
        <SearchInput
          type="text"
          placeholder="Search books..."
          aria-label="Search books"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
      )}

      {filteredBooks.length === 0 ? (
        <StateBox>{books.length ? 'No books match this search.' : 'No books yet. Convert your first PDF.'}</StateBox>
      ) : (
        <BooksGrid>
          {filteredBooks.map((book) => (
            <BookCard key={book.id}>
              <BookName>{book.title || book.original_filename || 'Untitled book'}</BookName>
              <BookMeta>
                <div>File: {book.original_filename || 'Unknown'}</div>
                <div>Size: {formatFileSize(book.file_size)}</div>
                <div>Pages: {book.pages || 0}</div>
                <div>Words: {(book.words || 0).toLocaleString()}</div>
              </BookMeta>

              <Actions>
                <Button type="button" onClick={() => onOpenBook && onOpenBook(book)}>
                  Read
                </Button>
                <Button type="button" onClick={() => downloadBook(book)}>
                  Download
                </Button>
                <Button type="button" $danger onClick={() => deleteBook(book.id)}>
                  Delete
                </Button>
              </Actions>
            </BookCard>
          ))}
        </BooksGrid>
      )}

      {error && <StateBox $error>{error}</StateBox>}
    </DashboardContainer>
  );
};

export default UserDashboard;
