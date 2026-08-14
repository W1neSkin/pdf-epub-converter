import React from 'react';
import styled from 'styled-components';

// Plain FAQ text for Google and AI search. Keep answers short and true.

const Section = styled.section`
  margin: 4rem 0 2rem;
  color: white;
`;

const Title = styled.h2`
  font-size: 2rem;
  font-weight: 300;
  text-align: center;
  margin-bottom: 2rem;
`;

const List = styled.div`
  max-width: 720px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 1rem;
`;

const Item = styled.article`
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 0.75rem;
  padding: 1.25rem 1.5rem;
`;

const Question = styled.h3`
  font-size: 1.1rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
`;

const Answer = styled.p`
  color: rgba(255, 255, 255, 0.85);
  line-height: 1.6;
  font-size: 0.95rem;
`;

const Footer = styled.footer`
  margin-top: 3rem;
  text-align: center;
  color: rgba(255, 255, 255, 0.7);
  font-size: 0.9rem;
  line-height: 1.6;
`;

const faqs = [
  {
    q: 'What is this PDF to EPUB converter?',
    a: 'A free website that turns a PDF into an EPUB. Upload a file, wait for conversion, then download the book or read it here.'
  },
  {
    q: 'Is it free?',
    a: 'Yes. Create a free account. There is no paid plan on this site today.'
  },
  {
    q: 'What are the limits?',
    a: 'Each PDF can be up to 50MB and 100 pages.'
  },
  {
    q: 'Where can I read the EPUB?',
    a: 'In the built-in reader, or in apps that open EPUB files such as Apple Books and Google Play Books.'
  }
];

function LandingFaq() {
  return (
    <Section id="faq" aria-labelledby="faq-title">
      <Title id="faq-title">Questions</Title>
      <List>
        {faqs.map((item) => (
          <Item key={item.q}>
            <Question>{item.q}</Question>
            <Answer>{item.a}</Answer>
          </Item>
        ))}
      </List>
      <Footer>
        PDF to EPUB Converter is a free web app.
        It is not a local shop and has no office address.
        Use it from any country in a browser.
      </Footer>
    </Section>
  );
}

export default LandingFaq;
