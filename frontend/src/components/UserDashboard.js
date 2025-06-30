import React, { useState, useEffect } from 'react';
import styled from 'styled-components';

const DashboardContainer = styled.div`
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
`;

const StatsGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
`;

const StatCard = styled.div`
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-radius: 0.5rem;
  padding: 1.5rem;
  border: 1px solid rgba(255, 255, 255, 0.2);
  text-align: center;
`;

const StatNumber = styled.div`
  font-size: 2rem;
  font-weight: bold;
  color: #ffd700;
  margin-bottom: 0.5rem;
`;

const StatLabel = styled.div`
  color: rgba(255, 255, 255, 0.8);
  font-size: 0.9rem;
`;

const BooksGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1rem;
  margin-top: 2rem;
`;

const BookCard = styled.div`
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-radius: 0.5rem;
  padding: 1rem;
  border: 1px solid rgba(255, 255, 255, 0.2);
  transition: transform 0.2s ease;
  
  &:hover {
    transform: translateY(-2px);
  }
`;

const BookTitle = styled.h3`
  color: white;
  margin-bottom: 0.5rem;
  font-size: 1.1rem;
`;

const BookInfo = styled.div`
  color: rgba(255, 255, 255, 0.7);
  font-size: 0.9rem;
  margin-bottom: 0.5rem;
`;

const BookActions = styled.div`
  display: flex;
  gap: 0.5rem;
  margin-top: 1rem;
`;

const ActionButton = styled.button`
  background: ${props => props.danger ? '#ff6b6b' : 'rgba(255, 215, 0, 0.2)'};
  color: ${props => props.danger ? 'white' : '#ffd700'};
  border: 1px solid ${props => props.danger ? '#ff6b6b' : '#ffd700'};
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  cursor: pointer;
  font-size: 0.8rem;
  transition: all 0.3s ease;
  
  &:hover {
    background: ${props => props.danger ? '#ff5252' : 'rgba(255, 215, 0, 0.3)'};
  }
`;

const LoadingSpinner = styled.div`
  text-align: center;
  color: white;
  padding: 2rem;
  
  i {
    font-size: 2rem;
    animation: spin 1s linear infinite;
  }
  
  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
`;

const EmptyState = styled.div`
  text-align: center;
  color: rgba(255, 255, 255, 0.7);
  padding: 3rem;
  
  i {
    font-size: 3rem;
    margin-bottom: 1rem;
    color: rgba(255, 255, 255, 0.3);
  }
`;

const SectionTitle = styled.h2`
  color: white;
  margin-bottom: 1rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  
  i {
    color: #ffd700;
  }
`;

const API_BASE_URL = process.env.REACT_APP_API_URL || 'https://pdf-converter-api-gateway.onrender.com';

const UserDashboard = ({ user }) => {
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState(null);
  const [books, setBooks] = useState([]);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchUserData();
  }, []);

  const fetchUserData = async () => {
    try {
      const token = localStorage.getItem('authToken');
      if (!token) return;

      // Fetch library stats
      const statsResponse = await fetch(`${API_BASE_URL}/library/stats`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (statsResponse.ok) {
        const statsResult = await statsResponse.json();
        setStats(statsResult.data);
      }

      // Fetch user books
      const booksResponse = await fetch(`${API_BASE_URL}/library/books?limit=20`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (booksResponse.ok) {
        const booksResult = await booksResponse.json();
        setBooks(booksResult.data || []);
      }

    } catch (error) {
      setError('Failed to load dashboard data');
      console.error('Dashboard error:', error);
    } finally {
      setLoading(false);
    }
  };

  const deleteBook = async (bookId) => {
    if (!window.confirm('Are you sure you want to delete this book?')) return;

    try {
      const token = localStorage.getItem('authToken');
      const response = await fetch(`${API_BASE_URL}/library/books/${bookId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        setBooks(books.filter(book => book.id !== bookId));
        // Refresh stats
        fetchUserData();
      } else {
        alert('Failed to delete book');
      }
    } catch (error) {
      alert('Error deleting book');
      console.error('Delete error:', error);
    }
  };

  const downloadBook = (book) => {
    if (book.cloudinary_url) {
      window.open(book.cloudinary_url, '_blank');
    } else {
      alert('Download link not available');
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString();
  };

  if (loading) {
    return (
      <LoadingSpinner>
        <i className="fas fa-spinner"></i>
        <div>Loading your dashboard...</div>
      </LoadingSpinner>
    );
  }

  return (
    <DashboardContainer>
      <SectionTitle>
        <i className="fas fa-chart-bar"></i>
        Your Library Statistics
      </SectionTitle>
      
      {stats && (
        <StatsGrid>
          <StatCard>
            <StatNumber>{stats.total_books || 0}</StatNumber>
            <StatLabel>Total Books</StatLabel>
          </StatCard>
          <StatCard>
            <StatNumber>{formatFileSize(stats.total_size || 0)}</StatNumber>
            <StatLabel>Storage Used</StatLabel>
          </StatCard>
          <StatCard>
            <StatNumber>{stats.total_pages || 0}</StatNumber>
            <StatLabel>Total Pages</StatLabel>
          </StatCard>
          <StatCard>
            <StatNumber>{stats.recent_conversions || 0}</StatNumber>
            <StatLabel>Recent Conversions</StatLabel>
          </StatCard>
        </StatsGrid>
      )}

      <SectionTitle>
        <i className="fas fa-books"></i>
        Your Books ({books.length})
      </SectionTitle>

      {books.length === 0 ? (
        <EmptyState>
          <i className="fas fa-book-open"></i>
          <div>No books in your library yet</div>
          <div style={{ marginTop: '0.5rem', fontSize: '0.9rem' }}>
            Start by converting a PDF to EPUB!
          </div>
        </EmptyState>
      ) : (
        <BooksGrid>
          {books.map((book) => (
            <BookCard key={book.id}>
              <BookTitle>{book.title}</BookTitle>
              <BookInfo>
                <div><strong>Original:</strong> {book.original_filename}</div>
                <div><strong>Size:</strong> {formatFileSize(book.file_size)}</div>
                {book.pages && <div><strong>Pages:</strong> {book.pages}</div>}
                {book.words && <div><strong>Words:</strong> {book.words.toLocaleString()}</div>}
                <div><strong>Created:</strong> {formatDate(book.created_at)}</div>
              </BookInfo>
              <BookActions>
                <ActionButton onClick={() => downloadBook(book)}>
                  <i className="fas fa-download"></i> Download
                </ActionButton>
                <ActionButton danger onClick={() => deleteBook(book.id)}>
                  <i className="fas fa-trash"></i> Delete
                </ActionButton>
              </BookActions>
            </BookCard>
          ))}
        </BooksGrid>
      )}

      {error && (
        <div style={{ 
          color: '#ff6b6b', 
          textAlign: 'center', 
          margin: '2rem 0',
          padding: '1rem',
          background: 'rgba(255, 107, 107, 0.1)',
          borderRadius: '0.5rem'
        }}>
          {error}
        </div>
      )}
    </DashboardContainer>
  );
};

export default UserDashboard; 