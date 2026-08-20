import React, { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import styled from 'styled-components';
import AuthForm from './AuthForm';
import LandingFaq from './LandingFaq';

const Page = styled.section`
  width: 100%;
`;

const LandingContent = styled.div`
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

const SectionTitle = styled.h2`
  margin-bottom: 0.8rem;
  font-size: 1.35rem;
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
  max-height: calc(100vh - 2rem);
  overflow-y: auto;
  position: relative;
  border-radius: 0.9rem;
  background: #111827;
  box-shadow: 0 1.5rem 4rem rgba(0, 0, 0, 0.55);
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

const LandingPage = ({ authRequest = 0, onAuthSuccess }) => {
  const [showAuthModal, setShowAuthModal] = useState(false);
  const modalRef = useRef(null);
  const closeButtonRef = useRef(null);

  useEffect(() => {
    if (authRequest > 0) {
      setShowAuthModal(true);
    }
  }, [authRequest]);

  useEffect(() => {
    if (!showAuthModal) return undefined;

    const previousFocus = document.activeElement;
    const previousOverflow = document.body.style.overflow;
    const appRoot = document.getElementById('root');
    document.body.style.overflow = 'hidden';
    appRoot?.setAttribute('inert', '');
    appRoot?.setAttribute('aria-hidden', 'true');
    closeButtonRef.current?.focus();

    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        setShowAuthModal(false);
        return;
      }
      if (event.key !== 'Tab' || !modalRef.current) return;

      const controls = modalRef.current.querySelectorAll(
        'button:not(:disabled), input:not(:disabled), [href]'
      );
      if (!controls.length) return;

      const firstControl = controls[0];
      const lastControl = controls[controls.length - 1];
      if (event.shiftKey && document.activeElement === firstControl) {
        event.preventDefault();
        lastControl.focus();
      } else if (!event.shiftKey && document.activeElement === lastControl) {
        event.preventDefault();
        firstControl.focus();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = previousOverflow;
      appRoot?.removeAttribute('inert');
      appRoot?.removeAttribute('aria-hidden');
      previousFocus?.focus();
    };
  }, [showAuthModal]);

  return (
    <Page>
      <LandingContent
        inert={showAuthModal ? true : undefined}
        aria-hidden={showAuthModal ? 'true' : undefined}
      >
        <Hero>
          <HeroTitle>PDF to EPUB or Excel — without the guesswork</HeroTitle>
          <HeroText>
            Choose a book for reading or a spreadsheet for working with document
            data. The free plan supports PDF files up to 50MB and 50 pages.
          </HeroText>
          <CTA type="button" onClick={() => setShowAuthModal(true)}>
            Start converting
          </CTA>
        </Hero>

        <Card>
          <SectionTitle>Choose what you need</SectionTitle>
          <Grid>
            <Card>
              <CardTitle>EPUB book</CardTitle>
              <CardText>
                Preserves the original PDF pages and adds selectable text. Read it
                in the browser or download the EPUB.
              </CardText>
            </Card>
            <Card>
              <CardTitle>Excel + tables</CardTitle>
              <CardText>
                Creates a readable XLSX workbook, one combined CSV, and a ZIP with
                separate tables.
              </CardText>
            </Card>
          </Grid>
        </Card>

        <Grid aria-label="Free plan limits">
          <Card>
            <CardTitle>50 MB maximum</CardTitle>
            <CardText>Maximum PDF file size on the free plan.</CardText>
          </Card>
          <Card>
            <CardTitle>50 pages maximum</CardTitle>
            <CardText>Maximum page count on the free plan.</CardText>
          </Card>
        </Grid>

        <LandingFaq />
      </LandingContent>
      {showAuthModal && createPortal(
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
          <ModalInner ref={modalRef}>
            <CloseButton
              ref={closeButtonRef}
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
        </Modal>,
        document.body
      )}
    </Page>
  );
};

export default LandingPage;
