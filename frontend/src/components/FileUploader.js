import React, { useCallback, useState } from 'react';
import styled from 'styled-components';

const UploaderContainer = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2rem;
  max-width: 600px;
  width: 100%;
`;

const DropZone = styled.div`
  border: 3px dashed ${props => props.isDragActive ? '#ffd700' : 'rgba(255, 255, 255, 0.3)'};
  border-radius: 1rem;
  padding: 3rem 2rem;
  text-align: center;
  background: ${props => props.isDragActive ? 'rgba(255, 215, 0, 0.1)' : 'rgba(255, 255, 255, 0.1)'};
  backdrop-filter: blur(10px);
  cursor: pointer;
  transition: all 0.3s ease;
  width: 100%;

  &:hover {
    border-color: #ffd700;
    background: rgba(255, 215, 0, 0.1);
    transform: translateY(-2px);
  }
`;

const UploadIcon = styled.i`
  font-size: 4rem;
  color: #ffd700;
  margin-bottom: 1rem;
`;

const UploadText = styled.div`
  color: white;
  font-size: 1.2rem;
  margin-bottom: 0.5rem;
`;

const UploadSubtext = styled.div`
  color: rgba(255, 255, 255, 0.7);
  font-size: 0.9rem;
`;

const HiddenInput = styled.input`
  display: none;
`;

const SampleSection = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  padding: 2rem;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-radius: 1rem;
  border: 1px solid rgba(255, 255, 255, 0.2);
  width: 100%;
`;

const SampleTitle = styled.h3`
  color: white;
  font-weight: 300;
  margin-bottom: 0.5rem;
`;

const SampleButton = styled.button`
  background: linear-gradient(45deg, #ff6b6b, #ee5a24);
  border: none;
  color: white;
  padding: 0.8rem 1.5rem;
  border-radius: 0.5rem;
  cursor: pointer;
  font-size: 1rem;
  font-weight: 500;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 0.5rem;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 15px rgba(238, 90, 36, 0.4);
  }
`;

const FileUploader = ({ onFileSelect }) => {
  const [isDragActive, setIsDragActive] = useState(false);
  const fileInputRef = React.useRef();

  const handleDrag = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setIsDragActive(true);
    } else if (e.type === "dragleave") {
      setIsDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (file.type === 'application/epub+zip' || file.name.endsWith('.epub')) {
        onFileSelect(file);
      } else {
        alert('Please select a valid EPUB file.');
      }
    }
  }, [onFileSelect]);

  const handleChange = useCallback((e) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (file.type === 'application/epub+zip' || file.name.endsWith('.epub')) {
        onFileSelect(file);
      } else {
        alert('Please select a valid EPUB file.');
      }
    }
  }, [onFileSelect]);

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  const loadSampleEpub = async () => {
    try {
      // Load the sample EPUB from frontend public folder
      const response = await fetch('/sample1.epub');
      if (response.ok) {
        const blob = await response.blob();
        const file = new File([blob], 'sample1.epub', { type: 'application/epub+zip' });
        onFileSelect(file);
      } else {
        alert('Sample EPUB not found. Please upload your own EPUB file.');
      }
    } catch (error) {
      alert('Could not load sample EPUB. Please upload your own EPUB file.');
    }
  };

  return (
    <UploaderContainer>
      <DropZone
        isDragActive={isDragActive}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={handleClick}
      >
        <UploadIcon className="fas fa-cloud-upload-alt" />
        <UploadText>
          {isDragActive ? "Drop your EPUB file here" : "Drop an EPUB file here or click to browse"}
        </UploadText>
        <UploadSubtext>
          Supports .epub files
        </UploadSubtext>
        <HiddenInput
          ref={fileInputRef}
          type="file"
          accept=".epub,application/epub+zip"
          onChange={handleChange}
        />
      </DropZone>

      <SampleSection>
        <SampleTitle>Or try our sample EPUB</SampleTitle>
        <SampleButton onClick={loadSampleEpub}>
          <i className="fas fa-file-alt"></i>
          Load Sample Document
        </SampleButton>
      </SampleSection>
    </UploaderContainer>
  );
};

export default FileUploader; 