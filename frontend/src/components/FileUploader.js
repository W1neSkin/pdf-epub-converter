import React, { useCallback, useRef, useState } from 'react';
import styled from 'styled-components';

const Wrapper = styled.section`
  width: 100%;
  max-width: 760px;
  margin: 0 auto;
`;

const Card = styled.div`
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-radius: 1rem;
  background: rgba(255, 255, 255, 0.08);
  padding: 1.2rem;
`;

const DropZone = styled.div`
  border: 2px dashed ${(props) => (props.$active ? '#facc15' : 'rgba(255, 255, 255, 0.35)')};
  border-radius: 0.9rem;
  background: ${(props) => (props.$active ? 'rgba(250, 204, 21, 0.12)' : 'rgba(255, 255, 255, 0.03)')};
  text-align: center;
  padding: 2rem 1rem;
`;

const HiddenInput = styled.input`
  display: none;
`;

const ChooseButton = styled.button`
  margin-top: 1rem;
  border: none;
  border-radius: 0.65rem;
  background: #facc15;
  color: #111827;
  font-weight: 700;
  min-height: 2.8rem;
  padding: 0.4rem 1.1rem;
  cursor: pointer;
`;

const ErrorText = styled.div`
  margin-top: 0.8rem;
  color: #fecaca;
`;

const FileUploader = ({ onFileSelect }) => {
  const [isDragActive, setIsDragActive] = useState(false);
  const [error, setError] = useState('');
  const inputRef = useRef(null);

  const selectFile = useCallback((file) => {
    if (!file) return;
    const isEpub = file.type === 'application/epub+zip' || file.name.toLowerCase().endsWith('.epub');
    if (!isEpub) {
      setError('Please choose an EPUB file.');
      return;
    }
    setError('');
    onFileSelect(file);
  }, [onFileSelect]);

  const handleDrag = useCallback((event) => {
    event.preventDefault();
    event.stopPropagation();
    if (event.type === 'dragenter' || event.type === 'dragover') {
      setIsDragActive(true);
    } else if (event.type === 'dragleave') {
      setIsDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((event) => {
    event.preventDefault();
    event.stopPropagation();
    setIsDragActive(false);
    const file = event.dataTransfer?.files?.[0];
    selectFile(file);
  }, [selectFile]);

  return (
    <Wrapper>
      <Card>
        <DropZone
          $active={isDragActive}
          onDragEnter={handleDrag}
          onDragOver={handleDrag}
          onDragLeave={handleDrag}
          onDrop={handleDrop}
        >
          <i className="fas fa-book-open" style={{ fontSize: '2.6rem', color: '#facc15' }} aria-hidden="true"></i>
          <h3 style={{ margin: '0.7rem 0 0.35rem' }}>Open an EPUB file</h3>
          <p style={{ color: 'rgba(255,255,255,0.8)' }}>
            Drop an EPUB here or choose a file manually.
          </p>
          <ChooseButton type="button" onClick={() => inputRef.current?.click()}>
            Choose EPUB
          </ChooseButton>
          <HiddenInput
            ref={inputRef}
            type="file"
            accept=".epub,application/epub+zip"
            onChange={(event) => selectFile(event.target.files?.[0])}
          />
          {error && <ErrorText>{error}</ErrorText>}
        </DropZone>
      </Card>
    </Wrapper>
  );
};

export default FileUploader;
