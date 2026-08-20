import styled from 'styled-components';


export const Panel = styled.div`
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 0.9rem;
  background: rgba(255, 255, 255, 0.07);
  padding: clamp(1rem, 2vw, 1.35rem);
`;

const BaseButton = styled.button`
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.45rem;
  min-height: 2.75rem;
  border-radius: 0.65rem;
  padding: 0.55rem 1rem;
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
  border: 1px solid #facc15;
  background: #facc15;
  color: #111827;

  &:hover:not(:disabled) {
    background: #fde047;
  }
`;

export const SecondaryAction = styled(BaseButton)`
  border: 1px solid rgba(255, 255, 255, 0.24);
  background: rgba(255, 255, 255, 0.06);
  color: #ffffff;

  &:hover:not(:disabled) {
    background: rgba(255, 255, 255, 0.12);
    border-color: rgba(255, 255, 255, 0.38);
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
    props.$active ? '#facc15' : 'rgba(255, 255, 255, 0.3)'
  )};
  border-radius: 0.85rem;
  background: ${(props) => (
    props.$active ? 'rgba(250, 204, 21, 0.1)' : 'rgba(15, 23, 42, 0.38)'
  )};
  padding: clamp(1.5rem, 5vw, 2.4rem) 1rem;
  text-align: center;
  transition: border-color 0.2s ease, background 0.2s ease;
`;

export const MutedText = styled.p`
  color: rgba(255, 255, 255, 0.72);
  line-height: 1.55;
`;
