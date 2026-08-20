import React, { useCallback, useEffect, useState } from 'react';
import styled, { createGlobalStyle } from 'styled-components';
import '@fortawesome/fontawesome-free/css/all.min.css';
import EpubReader from './components/EpubReader';
import FileUploader from './components/FileUploader';
import PdfUploader from './components/PdfUploader';
import LandingPage from './components/LandingPage';
import UserDashboard from './components/UserDashboard';
import { API_BASE_URL, AUTH_BASE_URL } from './config';

const GlobalStyle = createGlobalStyle`
  * {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
  }

  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background:
      radial-gradient(circle at 50% -15%, rgba(49, 67, 116, 0.45), transparent 38rem),
      #0a1020;
    color: #ffffff;
    min-height: 100vh;
  }

  button,
  input {
    font: inherit;
  }

  button:focus-visible,
  input:focus-visible,
  a:focus-visible {
    outline: 3px solid rgba(250, 204, 21, 0.4);
    outline-offset: 2px;
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
  background: rgba(10, 16, 32, 0.92);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.12);
  padding: 0.75rem 1rem;

  @media (max-width: 720px) {
    padding: 0.5rem 0.65rem;
  }
`;

const HeaderRow = styled.div`
  max-width: 1180px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: minmax(180px, 1fr) auto minmax(180px, 1fr);
  align-items: center;
  gap: 0.75rem;

  @media (max-width: 720px) {
    grid-template-columns: auto 1fr auto;
    gap: 0.4rem;
  }
`;

const BrandButton = styled.button`
  display: flex;
  align-items: center;
  gap: 0.55rem;
  background: transparent;
  border: none;
  color: #ffffff;
  cursor: pointer;
  font-size: 1.05rem;
  font-weight: 750;

  i {
    color: #facc15;
  }

  @media (max-width: 720px) {
    width: 2.6rem;
    height: 2.6rem;
    justify-content: center;

    span {
      display: none;
    }
  }
`;

const UserPanel = styled.div`
  display: flex;
  align-items: center;
  gap: 0.6rem;
  flex-wrap: wrap;
  justify-self: end;
`;

const UserChip = styled.div`
  background: #121a2d;
  border: 1px solid #27324a;
  border-radius: 999px;
  padding: 0.4rem 0.8rem;
  color: rgba(255, 255, 255, 0.9);
  font-size: 0.88rem;
  max-width: 280px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;

  @media (max-width: 720px) {
    display: none;
  }
`;

const TopButton = styled.button`
  border: 1px solid rgba(255, 255, 255, 0.22);
  border-radius: 0.5rem;
  padding: 0.7rem 0.9rem;
  background: ${(props) => (props.$accent ? '#facc15' : 'rgba(255, 255, 255, 0.08)')};
  color: ${(props) => (props.$accent ? '#111827' : '#ffffff')};
  cursor: pointer;
  font-weight: 600;
  justify-self: end;

  @media (min-width: 721px) {
    grid-column: 3;
  }

  @media (max-width: 720px) {
    width: 2.6rem;
    height: 2.6rem;
    padding: 0;

    span {
      display: none;
    }
  }
`;

const NavBar = styled.nav`
  margin: 0;
  display: flex;
  gap: 0.2rem;
  padding: 0.25rem;
  border: 1px solid #27324a;
  border-radius: 0.85rem;
  background: #0d1526;

  @media (max-width: 720px) {
    grid-column: auto;
    grid-row: auto;
    display: grid;
    grid-template-columns: 1fr 1fr;
    padding: 0.15rem;
  }
`;

const NavButton = styled.button`
  border: 1px solid transparent;
  border-radius: 0.62rem;
  padding: 0.58rem 0.9rem;
  background: ${(props) => (props.$active ? '#202a40' : 'transparent')};
  color: ${(props) => (props.$active ? '#ffffff' : 'rgba(255, 255, 255, 0.68)')};
  cursor: pointer;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  justify-content: center;
  box-shadow: ${(props) => (props.$active ? 'inset 0 -2px #f7c948' : 'none')};

  &:hover {
    color: #ffffff;
    background: #182238;
  }

  @media (max-width: 720px) {
    padding: 0.5rem 0.6rem;
  }
`;

const Main = styled.main`
  flex: 1;
  width: 100%;
  max-width: 1180px;
  margin: 0 auto;
  padding: clamp(1.25rem, 3vw, 2.25rem) 1rem 3rem;
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
  const [landingAuthRequest, setLandingAuthRequest] = useState(0);

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

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000);

    fetch(`${AUTH_BASE_URL}/auth/verify`, {
      headers: { Authorization: `Bearer ${token}` },
      signal: controller.signal,
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
      .finally(() => {
        clearTimeout(timeoutId);
        setAuthChecked(true);
      });
  }, []);

  const goDashboard = useCallback(() => {
    setCurrentView(VIEW_DASHBOARD);
    setEpubFile(null);
    setEpubUrl(null);
  }, []);

  const handleLogin = useCallback((userData, destination = VIEW_DASHBOARD) => {
    setUser(userData);
    setLandingAuthRequest(0);
    setEpubFile(null);
    setEpubUrl(null);
    setCurrentView(destination);
  }, []);

  const handleLogout = useCallback(() => {
    setUser(null);
    setLandingAuthRequest(0);
    localStorage.removeItem('authToken');
    localStorage.removeItem('userData');
    setCurrentView(VIEW_DASHBOARD);
    setEpubFile(null);
    setEpubUrl(null);
  }, []);

  const handleSessionExpired = useCallback(() => {
    handleLogout();
  }, [handleLogout]);

  const handleFileSelect = useCallback((file) => {
    setEpubUrl(null);
    setEpubFile(file);
    setCurrentView(VIEW_READ);
  }, []);

  const openLocalEpub = useCallback(() => {
    setEpubFile(null);
    setEpubUrl(null);
    setCurrentView(VIEW_READ);
  }, []);

  const openConverter = useCallback(() => {
    setCurrentView(VIEW_CONVERT);
  }, []);

  const handleEpubGenerated = useCallback((url) => {
    if (!url) return;
    setEpubFile(null);
    setEpubUrl(url);
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
      return (
        <PdfUploader
          onBack={goDashboard}
          onEpubGenerated={handleEpubGenerated}
          user={user}
          onSessionExpired={handleSessionExpired}
        />
      );
    }
    if (currentView === VIEW_READ) {
      if (!epubFile && !epubUrl) {
        return (
          <ReaderUploadWrap>
            <FileUploader onFileSelect={handleFileSelect} onBack={goDashboard} />
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
    return (
      <UserDashboard
        user={user}
        onOpenBook={handleOpenLibraryBook}
        onNavigateToConvert={openConverter}
        onOpenLocalEpub={openLocalEpub}
      />
    );
  };

  return (
    <>
      <GlobalStyle />
      <AppShell>
        <Header>
          <HeaderRow>
            <BrandButton type="button" onClick={goDashboard}>
              <i className="fas fa-file-pdf" aria-hidden="true"></i>
              <span>PDF Converter</span>
            </BrandButton>

            {user && (
              <NavBar aria-label="Main navigation">
                <NavButton
                  type="button"
                  aria-label="Library"
                  $active={currentView === VIEW_DASHBOARD}
                  onClick={goDashboard}
                >
                  <i className="fas fa-book" aria-hidden="true"></i>
                  <span>Library</span>
                </NavButton>
                <NavButton
                  type="button"
                  aria-label="Convert"
                  $active={currentView === VIEW_CONVERT}
                  onClick={() => setCurrentView(VIEW_CONVERT)}
                >
                  <i className="fas fa-file-pdf" aria-hidden="true"></i>
                  <span>Convert</span>
                </NavButton>
              </NavBar>
            )}

            {user ? (
              <UserPanel>
                <UserChip title={user.email}>{user.email}</UserChip>
                <TopButton type="button" aria-label="Logout" onClick={handleLogout}>
                  <i className="fas fa-arrow-right-from-bracket" aria-hidden="true"></i>
                  <span>Logout</span>
                </TopButton>
              </UserPanel>
            ) : (
              <TopButton
                type="button"
                aria-label="Sign in"
                $accent
                onClick={() => setLandingAuthRequest((value) => value + 1)}
              >
                <i className="fas fa-user" aria-hidden="true"></i>
                <span>Sign in</span>
              </TopButton>
            )}
          </HeaderRow>
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
            <LandingPage
              authRequest={landingAuthRequest}
              onAuthSuccess={(userData) => handleLogin(userData, VIEW_CONVERT)}
            />
          ) : (
            renderAuthenticatedContent()
          )}
        </Main>
      </AppShell>
    </>
  );
}

export default App;
