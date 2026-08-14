import React, { useState } from 'react';
import styled, { keyframes } from 'styled-components';
import AuthForm from './AuthForm';
import LandingFaq from './LandingFaq';

const fadeIn = keyframes`
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
`;

const float = keyframes`
  0%, 100% {
    transform: translateY(0px);
  }
  50% {
    transform: translateY(-20px);
  }
`;

const pulse = keyframes`
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.05);
  }
`;

const slideIn = keyframes`
  from {
    opacity: 0;
    transform: translateX(-50px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
`;

const LandingContainer = styled.div`
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
`;

const HeroSection = styled.div`
  text-align: center;
  margin-bottom: 4rem;
  animation: ${fadeIn} 1s ease-out;
`;

const HeroTitle = styled.h1`
  font-size: 3.5rem;
  font-weight: 300;
  color: white;
  margin-bottom: 1rem;
  background: linear-gradient(135deg, #ffd700, #ffed4e, #ffd700);
  background-size: 200% 200%;
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  animation: ${pulse} 3s infinite;
  
  @media (max-width: 768px) {
    font-size: 2.5rem;
  }
`;

const HeroSubtitle = styled.p`
  font-size: 1.3rem;
  color: rgba(255, 255, 255, 0.9);
  margin-bottom: 2rem;
  line-height: 1.6;
  max-width: 600px;
  margin-left: auto;
  margin-right: auto;
  
  @media (max-width: 768px) {
    font-size: 1.1rem;
  }
`;

const CTAButton = styled.button`
  background: linear-gradient(135deg, #ffd700, #ffed4e);
  color: #333;
  border: none;
  padding: 1rem 2rem;
  font-size: 1.2rem;
  font-weight: bold;
  border-radius: 50px;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 8px 25px rgba(255, 215, 0, 0.3);
  
  &:hover {
    transform: translateY(-3px);
    box-shadow: 0 12px 35px rgba(255, 215, 0, 0.4);
  }
  
  &:active {
    transform: translateY(0);
  }
`;

const FeaturesGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 2rem;
  margin: 4rem 0;
`;

const FeatureCard = styled.div`
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-radius: 1rem;
  padding: 2rem;
  border: 1px solid rgba(255, 255, 255, 0.2);
  text-align: center;
  transition: all 0.3s ease;
  animation: ${fadeIn} 1s ease-out ${props => props.delay || '0s'};
  
  &:hover {
    transform: translateY(-10px);
    background: rgba(255, 255, 255, 0.15);
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
  }
`;

const FeatureIcon = styled.div`
  width: 80px;
  height: 80px;
  background: linear-gradient(135deg, #ffd700, #ffed4e);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 1rem;
  animation: ${float} 3s ease-in-out infinite;
  animation-delay: ${props => props.delay || '0s'};
  
  i {
    font-size: 2rem;
    color: #333;
  }
`;

const FeatureTitle = styled.h3`
  color: white;
  font-size: 1.3rem;
  margin-bottom: 1rem;
  font-weight: 500;
`;

const FeatureDescription = styled.p`
  color: rgba(255, 255, 255, 0.8);
  line-height: 1.6;
  font-size: 0.95rem;
`;

const StatsSection = styled.div`
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-radius: 1rem;
  padding: 3rem 2rem;
  margin: 4rem 0;
  border: 1px solid rgba(255, 255, 255, 0.2);
  animation: ${slideIn} 1s ease-out 0.5s both;
`;

const StatsGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 2rem;
  text-align: center;
`;

const StatItem = styled.div`
  animation: ${fadeIn} 1s ease-out ${props => props.delay || '0s'};
`;

const StatNumber = styled.div`
  font-size: 3rem;
  font-weight: bold;
  color: #ffd700;
  margin-bottom: 0.5rem;
  animation: ${pulse} 2s infinite;
  animation-delay: ${props => props.delay || '0s'};
`;

const StatLabel = styled.div`
  color: rgba(255, 255, 255, 0.8);
  font-size: 1rem;
`;

const ProcessSection = styled.div`
  margin: 4rem 0;
  text-align: center;
`;

const ProcessTitle = styled.h2`
  color: white;
  font-size: 2.5rem;
  margin-bottom: 3rem;
  font-weight: 300;
  animation: ${fadeIn} 1s ease-out;
`;

const ProcessSteps = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 2rem;
  max-width: 900px;
  margin: 0 auto;
`;

const ProcessStep = styled.div`
  position: relative;
  animation: ${slideIn} 1s ease-out ${props => props.delay || '0s'};
  
  &::after {
    content: '→';
    position: absolute;
    top: 50%;
    right: -1rem;
    transform: translateY(-50%);
    font-size: 2rem;
    color: #ffd700;
    
    @media (max-width: 768px) {
      display: none;
    }
  }
  
  &:last-child::after {
    display: none;
  }
`;

const StepNumber = styled.div`
  width: 50px;
  height: 50px;
  background: linear-gradient(135deg, #ffd700, #ffed4e);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 1rem;
  font-size: 1.5rem;
  font-weight: bold;
  color: #333;
  animation: ${pulse} 2s infinite;
  animation-delay: ${props => props.delay || '0s'};
`;

const StepTitle = styled.h4`
  color: white;
  margin-bottom: 0.5rem;
  font-size: 1.1rem;
`;

const StepDescription = styled.p`
  color: rgba(255, 255, 255, 0.8);
  font-size: 0.9rem;
  line-height: 1.5;
`;

const AuthModal = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 2rem;
  animation: ${fadeIn} 0.3s ease-out;
`;

const ModalContent = styled.div`
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(20px);
  border-radius: 1rem;
  padding: 2rem;
  border: 1px solid rgba(255, 255, 255, 0.2);
  position: relative;
  max-width: 500px;
  width: 100%;
  animation: ${fadeIn} 0.5s ease-out;
`;

const CloseButton = styled.button`
  position: absolute;
  top: 1rem;
  right: 1rem;
  background: transparent;
  border: none;
  color: white;
  font-size: 1.5rem;
  cursor: pointer;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
  
  &:hover {
    background: rgba(255, 255, 255, 0.1);
  }
`;

const LandingPage = ({ onAuthSuccess }) => {
  const [showAuthModal, setShowAuthModal] = useState(false);

  const features = [
    {
      icon: 'fas fa-file-pdf',
      title: 'PDF to EPUB',
      description: 'Upload a PDF. The site extracts text and images and builds an EPUB you can download.',
      delay: '0.2s'
    },
    {
      icon: 'fas fa-book-open',
      title: 'Read in the browser',
      description: 'Open the EPUB here, select text, and flip pages. No extra app required.',
      delay: '0.4s'
    },
    {
      icon: 'fas fa-cloud',
      title: 'Personal library',
      description: 'Signed-in users keep converted books in a private library and can open them again later.',
      delay: '0.6s'
    },
    {
      icon: 'fas fa-user-lock',
      title: 'Account required',
      description: 'Conversion and the library need a free login. Files are stored with your account, not as a public dump.',
      delay: '0.8s'
    },
    {
      icon: 'fas fa-ruler',
      title: 'Clear limits',
      description: 'Free plan: 50MB and 50 pages. Paid plans can raise this when we move to a larger host.',
      delay: '1.0s'
    },
    {
      icon: 'fas fa-mobile-alt',
      title: 'Works on phones',
      description: 'Use it in a desktop or phone browser. The EPUB also opens in Apple Books and similar readers.',
      delay: '1.2s'
    }
  ];

  const steps = [
    {
      number: 1,
      title: 'Upload PDF',
      description: 'Drag and drop or select your PDF file',
      delay: '0.2s'
    },
    {
      number: 2,
      title: 'Convert',
      description: 'Text and images are extracted and packed into an EPUB',
      delay: '0.4s'
    },
    {
      number: 3,
      title: 'EPUB Ready',
      description: 'Download or read directly in your browser',
      delay: '0.6s'
    }
  ];

  return (
    <LandingContainer>
      <HeroSection>
        <HeroTitle>
          Free PDF to EPUB Converter
        </HeroTitle>
        <HeroSubtitle>
          Upload a PDF and get an EPUB with selectable text. Read it in the
          browser or download it. Free plan: up to 50MB and 50 pages.
        </HeroSubtitle>
        <CTAButton onClick={() => setShowAuthModal(true)}>
          <i className="fas fa-rocket" style={{ marginRight: '0.5rem' }}></i>
          Start Converting Now - Free Account
        </CTAButton>
      </HeroSection>

      <StatsSection>
        <StatsGrid>
          <StatItem delay="0.2s">
            <StatNumber>50</StatNumber>
            <StatLabel>MB max file size</StatLabel>
          </StatItem>
          <StatItem delay="0.4s">
            <StatNumber>100</StatNumber>
            <StatLabel>pages max</StatLabel>
          </StatItem>
          <StatItem delay="0.6s">
            <StatNumber>Free</StatNumber>
            <StatLabel>account to convert</StatLabel>
          </StatItem>
          <StatItem delay="0.8s">
            <StatNumber>EPUB</StatNumber>
            <StatLabel>file you can download</StatLabel>
          </StatItem>
        </StatsGrid>
      </StatsSection>

      <ProcessSection>
        <ProcessTitle>How It Works</ProcessTitle>
        <ProcessSteps>
          {steps.map((step, index) => (
            <ProcessStep key={index} delay={step.delay}>
              <StepNumber delay={step.delay}>{step.number}</StepNumber>
              <StepTitle>{step.title}</StepTitle>
              <StepDescription>{step.description}</StepDescription>
            </ProcessStep>
          ))}
        </ProcessSteps>
      </ProcessSection>

      <FeaturesGrid>
        {features.map((feature, index) => (
          <FeatureCard key={index} delay={feature.delay}>
            <FeatureIcon delay={feature.delay}>
              <i className={feature.icon}></i>
            </FeatureIcon>
            <FeatureTitle>{feature.title}</FeatureTitle>
            <FeatureDescription>{feature.description}</FeatureDescription>
          </FeatureCard>
        ))}
      </FeaturesGrid>

      <div style={{ textAlign: 'center', marginTop: '4rem' }}>
        <CTAButton onClick={() => setShowAuthModal(true)}>
          <i className="fas fa-user-plus" style={{ marginRight: '0.5rem' }}></i>
          Create a free account
        </CTAButton>
      </div>

      <LandingFaq />

      {showAuthModal && (
        <AuthModal onClick={(e) => e.target === e.currentTarget && setShowAuthModal(false)}>
          <ModalContent>
            <CloseButton onClick={() => setShowAuthModal(false)}>
              <i className="fas fa-times"></i>
            </CloseButton>
            <AuthForm onAuthSuccess={(userData) => {
              setShowAuthModal(false);
              onAuthSuccess(userData);
            }} />
          </ModalContent>
        </AuthModal>
      )}
    </LandingContainer>
  );
};

export default LandingPage; 