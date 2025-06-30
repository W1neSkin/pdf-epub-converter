import React, { useState, useCallback, useEffect } from 'react';
import styled, { createGlobalStyle } from 'styled-components';
import '@fortawesome/fontawesome-free/css/all.min.css';
import EpubReader from './components/EpubReader';
import FileUploader from './components/FileUploader';
import PdfUploader from './components/PdfUploader';
import LandingPage from './components/LandingPage';
import UserDashboard from './components/UserDashboard';
import './App.css';

const GlobalStyle = createGlobalStyle`
  * {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
  }

  body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
  }
`;

const AppContainer = styled.div`
  min-height: 100vh;
  display: flex;
  flex-direction: column;
`;

const Header = styled.header`
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  padding: 1rem 2rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: space-between;
`;

const Logo = styled.h1`
  color: white;
  font-size: 1.8rem;
  font-weight: 300;
  display: flex;
  align-items: center;
  gap: 0.5rem;

  i {
    color: #ffd700;
  }
`;

const UserSection = styled.div`
  display: flex;
  align-items: center;
  gap: 1rem;
`;

const UserInfo = styled.div`
  color: white;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  
  i {
    color: #ffd700;
  }
`;

const HeaderButton = styled.button`
  background: ${props => props.primary ? 'linear-gradient(135deg, #ffd700, #ffed4e)' : 'rgba(255, 255, 255, 0.2)'};
  color: ${props => props.primary ? '#333' : 'white'};
  border: 1px solid ${props => props.primary ? 'transparent' : 'rgba(255, 255, 255, 0.3)'};
  padding: 0.5rem 1rem;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: all 0.3s ease;
  font-weight: ${props => props.primary ? 'bold' : 'normal'};
  
  &:hover {
    background: ${props => props.primary ? 'linear-gradient(135deg, #ffed4e, #ffd700)' : 'rgba(255, 255, 255, 0.3)'};
    transform: ${props => props.primary ? 'translateY(-1px)' : 'none'};
  }
`;

const MainContent = styled.main`
  flex: 1;
  padding: 2rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
`;

const NavigationTabs = styled.div`
  display: flex;
  gap: 0.5rem;
  margin-bottom: 2rem;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 0.5rem;
  padding: 0.25rem;
`;

const Tab = styled.button`
  background: ${props => props.active ? 'rgba(255, 215, 0, 0.3)' : 'transparent'};
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 0.25rem;
  cursor: pointer;
  transition: all 0.3s ease;
  font-weight: ${props => props.active ? 'bold' : 'normal'};
  
  &:hover {
    background: rgba(255, 215, 0, 0.2);
  }
`;

const WelcomeSection = styled.div`
  text-align: center;
  margin-bottom: 2rem;
`;

const WelcomeTitle = styled.h2`
  color: white;
  margin-bottom: 1rem;
  font-weight: 300;
`;

const WelcomeText = styled.p`
  color: rgba(255, 255, 255, 0.8);
  max-width: 600px;
  margin: 0 auto;
  line-height: 1.6;
`;

function App() {
  const [user, setUser] = useState(null);
  const [currentView, setCurrentView] = useState('dashboard'); // dashboard, convert, read
  const [epubFile, setEpubFile] = useState(null);
  const [authChecked, setAuthChecked] = useState(false);

  useEffect(() => {
    // Check for existing authentication on app load
    const token = localStorage.getItem('authToken');
    const userData = localStorage.getItem('userData');
    
    if (token && userData) {
      try {
        setUser(JSON.parse(userData));
      } catch (error) {
        console.error('Error parsing user data:', error);
        localStorage.removeItem('authToken');
        localStorage.removeItem('userData');
      }
    }
    setAuthChecked(true);
  }, []);

  const handleLogin = useCallback((userData) => {
    setUser(userData);
    setCurrentView('dashboard');
  }, []);

  const handleLogout = useCallback(() => {
    setUser(null);
    localStorage.removeItem('authToken');
    localStorage.removeItem('userData');
    setCurrentView('dashboard');
    setEpubFile(null);
  }, []);

  const handleFileSelect = useCallback((file) => {
    setEpubFile(file);
    setCurrentView('read');
  }, []);

  const handleBackToHome = useCallback(() => {
    setEpubFile(null);
    setCurrentView('dashboard');
  }, []);

  const getHeaderTitle = () => {
    if (!user) return { icon: 'fas fa-magic', text: 'PDF to EPUB Converter' };
    
    switch (currentView) {
      case 'convert':
        return { icon: 'fas fa-file-pdf', text: 'PDF to EPUB Converter' };
      case 'read':
        return { icon: 'fas fa-book-open', text: 'EPUB Reader' };
      default:
        return { icon: 'fas fa-tachometer-alt', text: 'My Library' };
    }
  };

  const headerInfo = getHeaderTitle();

  const renderMainContent = () => {
    // Show loading while checking auth
    if (!authChecked) {
      return (
        <div style={{ color: 'white', textAlign: 'center' }}>
          <i className="fas fa-spinner fa-spin" style={{ fontSize: '2rem', marginBottom: '1rem' }}></i>
          <div>Loading...</div>
        </div>
      );
    }

    // Show attractive landing page if not authenticated
    if (!user) {
      return <LandingPage onAuthSuccess={handleLogin} />;
    }

    // Authenticated user content
    switch (currentView) {
      case 'read':
        return <EpubReader epubFile={epubFile} />;
      
      case 'convert':
        return <PdfUploader onBack={handleBackToHome} user={user} />;
      
      case 'dashboard':
      default:
        return (
          <div style={{ width: '100%', maxWidth: '800px' }}>
            <WelcomeSection>
              <WelcomeTitle>
                Welcome back, {user.email}!
              </WelcomeTitle>
              <WelcomeText>
                Manage your personal library, convert new PDFs to EPUB format, and access all your converted books in one place.
              </WelcomeText>
            </WelcomeSection>

            <NavigationTabs>
              <Tab 
                active={currentView === 'dashboard'}
                onClick={() => setCurrentView('dashboard')}
              >
                <i className="fas fa-tachometer-alt" style={{ marginRight: '0.5rem' }}></i>
                My Library
              </Tab>
              <Tab 
                active={currentView === 'convert'}
                onClick={() => setCurrentView('convert')}
              >
                <i className="fas fa-file-pdf" style={{ marginRight: '0.5rem' }}></i>
                Convert PDF
              </Tab>
              <Tab 
                active={currentView === 'read'}
                onClick={() => setCurrentView('read')}
              >
                <i className="fas fa-book-open" style={{ marginRight: '0.5rem' }}></i>
                Read EPUB
              </Tab>
            </NavigationTabs>

            <div style={{ 
              display: 'flex', 
              gap: '1rem', 
              marginBottom: '2rem',
              justifyContent: 'center',
              flexWrap: 'wrap'
            }}>
              <HeaderButton
                primary
                onClick={() => setCurrentView('convert')}
              >
                <i className="fas fa-file-pdf" style={{ marginRight: '0.5rem' }}></i>
                Convert PDF to EPUB
              </HeaderButton>
              
              <HeaderButton
                onClick={() => setCurrentView('read')}
              >
                <i className="fas fa-book-open" style={{ marginRight: '0.5rem' }}></i>
                Read EPUB File
              </HeaderButton>
            </div>

            {currentView === 'dashboard' && <UserDashboard user={user} />}
            {currentView === 'read' && !epubFile && <FileUploader onFileSelect={handleFileSelect} />}
          </div>
        );
    }
  };

  return (
    <>
      <GlobalStyle />
      <AppContainer>
        <Header>
          <Logo onClick={() => user && setCurrentView('dashboard')} style={{ cursor: user ? 'pointer' : 'default' }}>
            <i className={headerInfo.icon}></i>
            {headerInfo.text}
          </Logo>
          
          <UserSection>
            {user ? (
              <>
                <UserInfo>
                  <i className="fas fa-user-circle"></i>
                  <span>{user.email}</span>
                </UserInfo>
                <HeaderButton onClick={() => setCurrentView('dashboard')}>
                  <i className="fas fa-tachometer-alt"></i> Dashboard
                </HeaderButton>
                <HeaderButton onClick={handleLogout}>
                  <i className="fas fa-sign-out-alt"></i> Logout
                </HeaderButton>
              </>
            ) : (
              <div style={{ color: 'rgba(255, 255, 255, 0.8)' }}>
                <i className="fas fa-info-circle" style={{ marginRight: '0.5rem' }}></i>
                Create an account to get started
              </div>
            )}
            
            {(user && currentView !== 'dashboard') && (
              <HeaderButton onClick={handleBackToHome}>
                <i className="fas fa-arrow-left"></i> Back
              </HeaderButton>
            )}
          </UserSection>
        </Header>
        
        <MainContent>
          {renderMainContent()}
        </MainContent>
      </AppContainer>
    </>
  );
}

export default App;
