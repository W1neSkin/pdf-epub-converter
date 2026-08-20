import styled from 'styled-components';


export const Panel = styled.div`
  border: 1px solid #27324a;
  border-radius: 1rem;
  background: #121a2d;
  box-shadow: 0 1rem 2.5rem rgba(2, 6, 23, 0.16);
  padding: clamp(1rem, 2vw, 1.5rem);
`;

const BaseButton = styled.button`
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.45rem;
  min-height: 2.75rem;
  border-radius: 0.7rem;
  padding: 0.6rem 1.05rem;
  cursor: pointer;
  font-weight: 700;
  transition: transform 0.15s ease, background 0.15s ease, border-color 0.15s ease;

  &:hover:not(:disabled) {
    transform: translateY(-1px);
  }

  &:focus-visible {
    outline: 3px solid rgba(250, 204, 21, 0.35);
    outline-offset: 2px;
  }

  &:disabled {
    cursor: not-allowed;
    opacity: 0.55;
  }
`;

export const PrimaryAction = styled(BaseButton)`
  border: 1px solid #f7c948;
  background: #f7c948;
  color: #111827;

  &:hover:not(:disabled) {
    background: #ffda63;
  }
`;

export const SecondaryAction = styled(BaseButton)`
  border: 1px solid #34415c;
  background: #1a2439;
  color: #ffffff;

  &:hover:not(:disabled) {
    background: #222e46;
    border-color: #4a5a79;
  }
`;

export const DangerAction = styled(SecondaryAction)`
  border-color: rgba(248, 113, 113, 0.55);
  color: #fecaca;

  &:hover:not(:disabled) {
    background: rgba(248, 113, 113, 0.12);
    border-color: rgba(248, 113, 113, 0.8);
  }
`;

export const ButtonRow = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
  align-items: center;
`;

export const DropArea = styled.div`
  border: 2px dashed ${(props) => (
    props.$active ? '#f7c948' : '#3a4763'
  )};
  border-radius: 1rem;
  background: ${(props) => (
    props.$active ? 'rgba(247, 201, 72, 0.1)' : '#0d1526'
  )};
  padding: clamp(2.5rem, 8vw, 5rem) 1.25rem;
  text-align: center;
  transition: border-color 0.2s ease, background 0.2s ease;
`;

export const MutedText = styled.p`
  color: rgba(255, 255, 255, 0.72);
  line-height: 1.55;
`;
