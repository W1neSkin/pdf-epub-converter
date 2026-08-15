import React, { useState } from 'react';
import styled from 'styled-components';
import AuthForm from './AuthForm';
import LandingFaq from './LandingFaq';

const Page = styled.section`
  width: 100%;
  display: grid;
  gap: 1.25rem;
`;

const Hero = styled.div`
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-radius: 1rem;
  background: rgba(15, 23, 42, 0.72);
  padding: clamp(1.1rem, 2.4vw, 2rem);
`;

const HeroTitle = styled.h1`
  font-size: clamp(1.7rem, 4vw, 2.7rem);
  line-height: 1.15;
`;

const HeroText = styled.p`
  margin-top: 0.85rem;
  color: rgba(255, 255, 255, 0.86);
  line-height: 1.6;
  max-width: 760px;
`;

const CTA = styled.button`
  margin-top: 1rem;
  border: none;
  border-radius: 0.7rem;
  padding: 0.75rem 1.1rem;
  background: #facc15;
  color: #111827;
  font-weight: 700;
  cursor: pointer;
`;

const Grid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 0.8rem;
`;

const Card = styled.article`
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 0.85rem;
  background: rgba(255, 255, 255, 0.07);
  padding: 0.95rem;
`;

const CardTitle = styled.h3`
  font-size: 1rem;
  margin-bottom: 0.45rem;
`;

const CardText = styled.p`
  color: rgba(255, 255, 255, 0.82);
  line-height: 1.5;
  font-size: 0.92rem;
`;

const StatValue = styled.div`
  font-size: 1.45rem;
  font-weight: 700;
  color: #facc15;
`;

const Steps = styled.ol`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: 0.8rem;
  list-style: none;
  counter-reset: step;
`;

const Step = styled.li`
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 0.85rem;
  background: rgba(255, 255, 255, 0.07);
  padding: 0.95rem;
  counter-increment: step;

  &::before {
    content: counter(step);
    display: inline-flex;
    width: 1.8rem;
    height: 1.8rem;
    border-radius: 999px;
    align-items: center;
    justify-content: center;
    background: #facc15;
    color: #111827;
    font-weight: 700;
    margin-bottom: 0.55rem;
  }
`;

const Modal = styled.div`
  position: fixed;
  inset: 0;
  background: rgba(2, 6, 23, 0.78);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  z-index: 1000;
`;

const ModalInner = styled.div`
  width: 100%;
  max-width: 460px;
  position: relative;
`;

const CloseButton = styled.button`
  position: absolute;
  right: 0.45rem;
  top: 0.45rem;
  width: 2.1rem;
  height: 2.1rem;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  background: rgba(255, 255, 255, 0.08);
  color: white;
  cursor: pointer;
  z-index: 2;
`;

const LandingPage = ({ onAuthSuccess }) => {
  const [showAuthModal, setShowAuthModal] = useState(false);

  return (
    <Page>
      <Hero>
        <HeroTitle>Free PDF to EPUB converter</HeroTitle>
        <HeroText>
          Upload a PDF and get a readable EPUB with selectable text. Free plan: up to 50 MB and 50 pages.
        </HeroText>
        <CTA type="button" onClick={() => setShowAuthModal(true)}>
          Start converting
        </CTA>
      </Hero>

      <Grid>
        <Card>
          <StatValue>50 MB</StatValue>
          <CardText>Maximum PDF file size on the free plan.</CardText>
        </Card>
        <Card>
          <StatValue>50 pages</StatValue>
          <CardText>Maximum page count on the free plan.</CardText>
        </Card>
        <Card>
          <StatValue>EPUB</StatValue>
          <CardText>Download or open converted books in the browser reader.</CardText>
        </Card>
      </Grid>

      <Card>
        <CardTitle>How it works</CardTitle>
        <Steps>
          <Step>
            <CardText>Upload a PDF by drag-and-drop or file picker.</CardText>
          </Step>
          <Step>
            <CardText>The service extracts text and builds a reflowable EPUB.</CardText>
          </Step>
          <Step>
            <CardText>Download the EPUB or open it from your library.</CardText>
          </Step>
        </Steps>
      </Card>

      <Grid>
        <Card>
          <CardTitle>Personal library</CardTitle>
          <CardText>Every converted book is saved in your account.</CardText>
        </Card>
        <Card>
          <CardTitle>In-browser reading</CardTitle>
          <CardText>Open EPUB files directly in the built-in reader.</CardText>
        </Card>
        <Card>
          <CardTitle>Cross-device</CardTitle>
          <CardText>Use desktop or mobile browser. EPUB also works in external apps.</CardText>
        </Card>
      </Grid>

      <LandingFaq />

      {showAuthModal && (
        <Modal
          role="dialog"
          aria-modal="true"
          aria-label="Authentication"
          onClick={(event) => {
            if (event.target === event.currentTarget) {
              setShowAuthModal(false);
            }
          }}
        >
          <ModalInner>
            <CloseButton
              type="button"
              aria-label="Close authentication dialog"
              onClick={() => setShowAuthModal(false)}
            >
              <i className="fas fa-times" aria-hidden="true"></i>
            </CloseButton>
            <AuthForm
              onAuthSuccess={(userData) => {
                setShowAuthModal(false);
                onAuthSuccess(userData);
              }}
            />
          </ModalInner>
        </Modal>
      )}
    </Page>
  );
};

export default LandingPage;
