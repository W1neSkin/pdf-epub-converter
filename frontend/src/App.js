import React, { useCallback, useEffect, useState } from 'react';
import styled, { createGlobalStyle } from 'styled-components';
import '@fortawesome/fontawesome-free/css/all.min.css';
import EpubReader from './components/EpubReader';
import FileUploader from './components/FileUploader';
import PdfUploader from './components/PdfUploader';
import LandingPage from './components/LandingPage';
import UserDashboard from './components/UserDashboard';
import { API_BASE_URL } from './config';

const GlobalStyle = createGlobalStyle`
  * {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
  }

  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: radial-gradient(circle at top, #1f2a56 0%, #111827 55%, #0b1120 100%);
    color: #ffffff;
    min-height: 100vh;
  }
`;

const AppShell = styled.div`
  min-height: 100vh;
  display: flex;
  flex-direction: column;
`;

const Header = styled.header`
  position: sticky;
  top: 0;
  z-index: 10;
  background: rgba(15, 23, 42, 0.88);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.12);
  padding: 0.9rem 1rem;
`;

const HeaderRow = styled.div`
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  flex-wrap: wrap;
`;

const BrandButton = styled.button`
  display: flex;
  align-items: center;
  gap: 0.55rem;
  background: transparent;
  border: none;
  color: #ffffff;
  cursor: pointer;
  font-size: 1.15rem;
  font-weight: 600;

  i {
    color: #facc15;
  }
`;

const UserPanel = styled.div`
  display: flex;
  align-items: center;
  gap: 0.6rem;
  flex-wrap: wrap;
`;

const UserChip = styled.div`
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-radius: 999px;
  padding: 0.4rem 0.8rem;
  color: rgba(255, 255, 255, 0.9);
  font-size: 0.88rem;
  max-width: 280px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
`;

const TopButton = styled.button`
  border: 1px solid rgba(255, 255, 255, 0.22);
  border-radius: 0.5rem;
  padding: 0.7rem 0.9rem;
  background: ${(props) => (props.$accent ? '#facc15' : 'rgba(255, 255, 255, 0.08)')};
  color: ${(props) => (props.$accent ? '#111827' : '#ffffff')};
  cursor: pointer;
  font-weight: 600;
`;

const NavBar = styled.nav`
  max-width: 1200px;
  margin: 0.65rem auto 0;
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
`;

const NavButton = styled.button`
  border: 1px solid ${(props) => (props.$active ? 'rgba(250, 204, 21, 0.9)' : 'rgba(255, 255, 255, 0.2)')};
  border-radius: 0.55rem;
  padding: 0.7rem 0.95rem;
  background: ${(props) => (props.$active ? 'rgba(250, 204, 21, 0.2)' : 'rgba(255, 255, 255, 0.05)')};
  color: #ffffff;
  cursor: pointer;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
`;

const Main = styled.main`
  flex: 1;
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 1.25rem 1rem 2rem;
`;

const LoadingState = styled.div`
  min-height: 60vh;
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(255, 255, 255, 0.9);
`;

const ReaderUploadWrap = styled.div`
  max-width: 720px;
  margin: 0 auto;
`;

const VIEW_DASHBOARD = 'dashboard';
const VIEW_CONVERT = 'convert';
const VIEW_READ = 'read';

function App() {
  const [user, setUser] = useState(null);
  const [currentView, setCurrentView] = useState(VIEW_DASHBOARD);
  const [epubFile, setEpubFile] = useState(null);
  const [epubUrl, setEpubUrl] = useState(null);
  const [authChecked, setAuthChecked] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('authToken');
    const userData = localStorage.getItem('userData');
    if (!token || !userData) {
      setAuthChecked(true);
      return;
    }

    let parsedUser = null;
    try {
      parsedUser = JSON.parse(userData);
    } catch (error) {
      localStorage.removeItem('authToken');
      localStorage.removeItem('userData');
      setAuthChecked(true);
      return;
    }

    fetch(`${API_BASE_URL}/auth/verify`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((response) => {
        if (response.ok || response.status >= 500) {
          setUser(parsedUser);
          return;
        }
        if (response.status === 401) {
          localStorage.removeItem('authToken');
          localStorage.removeItem('userData');
          setUser(null);
          return;
        }
        setUser(parsedUser);
      })
      .catch(() => setUser(parsedUser))
      .finally(() => setAuthChecked(true));
  }, []);

  const goDashboard = useCallback(() => {
    setCurrentView(VIEW_DASHBOARD);
    setEpubFile(null);
    setEpubUrl(null);
  }, []);

  const handleLogin = useCallback((userData) => {
    setUser(userData);
    goDashboard();
  }, [goDashboard]);

  const handleLogout = useCallback(() => {
    setUser(null);
    localStorage.removeItem('authToken');
    localStorage.removeItem('userData');
    setCurrentView(VIEW_DASHBOARD);
    setEpubFile(null);
    setEpubUrl(null);
  }, []);

  const handleFileSelect = useCallback((file) => {
    setEpubUrl(null);
    setEpubFile(file);
    setCurrentView(VIEW_READ);
  }, []);

  const handleOpenLibraryBook = useCallback((book) => {
    if (!book?.id) return;
    setEpubFile(null);
    setEpubUrl(`${API_BASE_URL}/library/books/${book.id}/file`);
    setCurrentView(VIEW_READ);
  }, []);

  const renderAuthenticatedContent = () => {
    if (currentView === VIEW_CONVERT) {
      return <PdfUploader onBack={goDashboard} user={user} />;
    }
    if (currentView === VIEW_READ) {
      if (!epubFile && !epubUrl) {
        return (
          <ReaderUploadWrap>
            <FileUploader onFileSelect={handleFileSelect} />
          </ReaderUploadWrap>
        );
      }
      return (
        <EpubReader
          epubFile={epubFile}
          epubUrl={epubUrl}
          token={user?.token}
          onBack={goDashboard}
        />
      );
    }
    return <UserDashboard user={user} onOpenBook={handleOpenLibraryBook} />;
  };

  return (
    <>
      <GlobalStyle />
      <AppShell>
        <Header>
          <HeaderRow>
            <BrandButton type="button" onClick={goDashboard}>
              <i className="fas fa-file-pdf" aria-hidden="true"></i>
              <span>PDF to EPUB Converter</span>
            </BrandButton>

            {user ? (
              <UserPanel>
                <UserChip title={user.email}>{user.email}</UserChip>
                <TopButton type="button" onClick={handleLogout}>
                  Logout
                </TopButton>
              </UserPanel>
            ) : (
              <div style={{ color: 'rgba(255,255,255,0.8)', fontSize: '0.95rem' }}>
                Free account required for conversion
              </div>
            )}
          </HeaderRow>

          {user && (
            <NavBar aria-label="Main navigation">
              <NavButton
                type="button"
                $active={currentView === VIEW_DASHBOARD}
                onClick={goDashboard}
              >
                <i className="fas fa-book" aria-hidden="true"></i>
                Library
              </NavButton>
              <NavButton
                type="button"
                $active={currentView === VIEW_CONVERT}
                onClick={() => setCurrentView(VIEW_CONVERT)}
              >
                <i className="fas fa-file-pdf" aria-hidden="true"></i>
                Convert PDF
              </NavButton>
              <NavButton
                type="button"
                $active={currentView === VIEW_READ}
                onClick={() => setCurrentView(VIEW_READ)}
              >
                <i className="fas fa-book-open" aria-hidden="true"></i>
                Read EPUB
              </NavButton>
            </NavBar>
          )}
        </Header>

        <Main>
          {!authChecked ? (
            <LoadingState>
              <div>
                <i className="fas fa-spinner fa-spin" style={{ marginRight: '0.6rem' }}></i>
                Loading...
              </div>
            </LoadingState>
          ) : !user ? (
            <LandingPage onAuthSuccess={handleLogin} />
          ) : (
            renderAuthenticatedContent()
          )}
        </Main>
      </AppShell>
    </>
  );
}

export default App;
