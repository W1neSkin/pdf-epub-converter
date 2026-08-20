import React, { useCallback, useRef, useState } from 'react';
import styled from 'styled-components';
import {
  ButtonRow,
  DropArea,
  Panel,
  PrimaryAction,
  SecondaryAction,
} from './ui';

const Wrapper = styled.section`
  width: 100%;
  max-width: 760px;
  margin: 0 auto;
`;

const HiddenInput = styled.input`
  display: none;
`;

const ErrorText = styled.div`
  margin-top: 0.8rem;
  color: #fecaca;
`;

const FileUploader = ({ onFileSelect, onBack }) => {
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
      <div style={{ marginBottom: '1rem' }}>
        <h2 style={{ marginBottom: '0.35rem' }}>Open EPUB from device</h2>
        <p style={{ color: 'rgba(255,255,255,0.72)' }}>
          Open an existing EPUB without adding it to your library.
        </p>
      </div>
      <Panel>
        <DropArea
          $active={isDragActive}
          onDragEnter={handleDrag}
          onDragOver={handleDrag}
          onDragLeave={handleDrag}
          onDrop={handleDrop}
        >
          <i className="fas fa-book-open" style={{ fontSize: '2.6rem', color: '#facc15' }} aria-hidden="true"></i>
          <h3 style={{ margin: '0.7rem 0 0.35rem' }}>Drop an EPUB here</h3>
          <p style={{ color: 'rgba(255,255,255,0.8)' }}>
            Or select a file from your device.
          </p>
          <ButtonRow style={{ justifyContent: 'center', marginTop: '1rem' }}>
            <PrimaryAction type="button" onClick={() => inputRef.current?.click()}>
              Choose EPUB
            </PrimaryAction>
            {onBack && (
              <SecondaryAction type="button" onClick={onBack}>
                Back to library
              </SecondaryAction>
            )}
          </ButtonRow>
          <HiddenInput
            ref={inputRef}
            type="file"
            accept=".epub,application/epub+zip"
            onChange={(event) => selectFile(event.target.files?.[0])}
          />
          {error && <ErrorText>{error}</ErrorText>}
        </DropArea>
      </Panel>
    </Wrapper>
  );
};

export default FileUploader;
