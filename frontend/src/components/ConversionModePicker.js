import React from 'react';
import styled from 'styled-components';


const Grid = styled.div`
  display: grid;
  grid-template-columns: ${(props) => (
    props.$stacked ? '1fr' : 'repeat(2, minmax(0, 1fr))'
  )};
  gap: 0.75rem;
  margin-bottom: 1rem;

  @media (max-width: 620px) {
    grid-template-columns: 1fr;
  }
`;

const Option = styled.button`
  min-height: 6.4rem;
  border: 1px solid ${(props) => (
    props.$active ? '#facc15' : 'rgba(255, 255, 255, 0.18)'
  )};
  border-radius: 0.8rem;
  background: ${(props) => (
    props.$active ? 'rgba(250, 204, 21, 0.13)' : 'rgba(255, 255, 255, 0.04)'
  )};
  color: #ffffff;
  padding: 1rem;
  text-align: left;
  cursor: pointer;

  &:hover {
    border-color: ${(props) => (
      props.$active ? '#facc15' : 'rgba(255, 255, 255, 0.38)'
    )};
  }

  &:focus-visible {
    outline: 3px solid rgba(250, 204, 21, 0.35);
    outline-offset: 2px;
  }
`;

const OptionHeader = styled.span`
  display: flex;
  align-items: center;
  gap: 0.65rem;
  font-size: 0.98rem;
  font-weight: 750;

  i {
    color: #facc15;
    width: 1.2rem;
    text-align: center;
  }
`;

const Description = styled.span`
  display: block;
  margin-top: 0.55rem;
  color: rgba(255, 255, 255, 0.72);
  line-height: 1.45;
  font-size: 0.9rem;
`;

const modes = [
  {
    id: 'epub',
    icon: 'fas fa-book-open',
    title: 'EPUB book',
    description: 'Best for reading. Preserves every PDF page and selectable text.',
  },
  {
    id: 'csv',
    icon: 'fas fa-table',
    title: 'Excel + tables',
    description: 'Best for data. Creates XLSX, one CSV, and separate table files.',
  },
];

const ConversionModePicker = ({ value, onChange, stacked = false }) => (
  <Grid aria-label="Output format" $stacked={stacked}>
    {modes.map((mode) => (
      <Option
        key={mode.id}
        type="button"
        $active={value === mode.id}
        aria-pressed={value === mode.id}
        onClick={() => onChange(mode.id)}
      >
        <OptionHeader>
          <i className={mode.icon} aria-hidden="true"></i>
          {mode.title}
        </OptionHeader>
        <Description>{mode.description}</Description>
      </Option>
    ))}
  </Grid>
);

export default ConversionModePicker;
