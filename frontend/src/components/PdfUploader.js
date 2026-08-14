import React, { useState, useCallback } from 'react';
import styled from 'styled-components';
import { API_BASE_URL } from '../config';

const UploaderContainer = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2rem;
  max-width: 600px;
  margin: 0 auto;
`;

const DropZone = styled.div`
  border: 3px dashed ${props => props.isDragOver ? '#ffd700' : 'rgba(255, 255, 255, 0.3)'};
  border-radius: 1rem;
  padding: 3rem;
  text-align: center;
  background: ${props => props.isDragOver ? 'rgba(255, 215, 0, 0.1)' : 'rgba(255, 255, 255, 0.05)'};
  backdrop-filter: blur(10px);
  transition: all 0.3s ease;
  cursor: pointer;
  min-height: 200px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
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

const ConversionStatus = styled.div`
  background: rgba(255, 255, 255, 0.1);
  border-radius: 0.5rem;
  padding: 1.5rem;
  color: white;
  text-align: center;
  width: 100%;
  max-width: 400px;
`;

const ProgressBar = styled.div`
  width: 100%;
  height: 6px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 3px;
  margin: 1rem 0;
  overflow: hidden;
`;

const ProgressFill = styled.div`
  height: 100%;
  background: linear-gradient(90deg, #ffd700, #ffed4e);
  border-radius: 3px;
  transition: width 0.3s ease;
  width: ${props => props.progress}%;
`;

const DownloadButton = styled.button`
  background: linear-gradient(135deg, #ffd700, #ffed4e);
  color: #333;
  border: none;
  padding: 1rem 2rem;
  border-radius: 0.5rem;
  font-weight: bold;
  cursor: pointer;
  transition: transform 0.2s ease;
  
  &:hover {
    transform: translateY(-2px);
  }
`;

const PdfUploader = ({ onEpubGenerated, onBack, user }) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const [isConverting, setIsConverting] = useState(false);
  const [conversionStatus, setConversionStatus] = useState('');
  const [downloadUrl, setDownloadUrl] = useState('');
  const [progress, setProgress] = useState(0);

  const uploadFile = useCallback(async (file) => {
    const isPdf = file && (
      file.type === 'application/pdf' ||
      file.name.toLowerCase().endsWith('.pdf')
    );
    if (!isPdf) {
      alert('Please select a valid PDF file');
      return;
    }

    const maxBytes = 50 * 1024 * 1024;
    if (file.size > maxBytes) {
      alert('PDF is too large. Maximum size is 50MB');
      return;
    }

    if (!user?.token) {
      alert('Authentication required. Please log in first.');
      return;
    }

    setIsConverting(true);
    setConversionStatus('Preparing upload...');
    setProgress(10);

    try {
      const formData = new FormData();
      formData.append('file', file);

      setConversionStatus('Uploading PDF...');
      setProgress(20);

      if (onEpubGenerated) {
        onEpubGenerated(null);
      }

      setConversionStatus('Processing PDF...');
      setProgress(40);

      const headers = {};
      if (user?.token) {
        headers['Authorization'] = `Bearer ${user.token}`;
      }

      const response = await fetch(`${API_BASE_URL}/api/convert`, {
        method: 'POST',
        headers,
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      const result = await response.json();

      if (!result.success || !result.conversion_id) {
        throw new Error(result.message || 'Conversion failed');
      }

      // Convert now returns immediately. Poll until the background job finishes.
      const maxAttempts = 150;
      const pollStatus = async (conversionId, attempt) => {
        const statusHeaders = { Authorization: `Bearer ${user.token}` };
        const statusResponse = await fetch(`${API_BASE_URL}/api/status/${conversionId}`, {
          headers: statusHeaders
        });
        if (!statusResponse.ok) {
          throw new Error(`Status check failed: ${statusResponse.status}`);
        }
        const statusData = await statusResponse.json();

        if (statusData.message) {
          setConversionStatus(statusData.message);
        }
        if (typeof statusData.progress === 'number') {
          setProgress(statusData.progress);
        }

        if (statusData.status === 'completed' && statusData.download_url) {
          setDownloadUrl(statusData.download_url);
          setConversionStatus('Conversion completed successfully!');
          setProgress(100);
          setIsConverting(false);
          if (onEpubGenerated) {
            onEpubGenerated(statusData.download_url);
          }
          return;
        }

        if (statusData.status === 'failed') {
          throw new Error(statusData.message || 'Conversion failed on server');
        }

        if (attempt >= maxAttempts) {
          throw new Error('Conversion timed out. Please try again.');
        }

        setTimeout(() => {
          pollStatus(conversionId, attempt + 1).catch((pollError) => {
            console.error('Upload error:', pollError);
            setConversionStatus(`Error: ${pollError.message}`);
            setProgress(0);
            setTimeout(() => {
              setIsConverting(false);
              setConversionStatus('');
            }, 3000);
          });
        }, 2000);
      };

      await pollStatus(result.conversion_id, 1);
    } catch (error) {
      console.error('Upload error:', error);
      setConversionStatus(`Error: ${error.message}`);
      setProgress(0);
      
      setTimeout(() => {
        setIsConverting(false);
        setConversionStatus('');
      }, 3000);
    }
  }, [user, onEpubGenerated]);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragOver(false);
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      uploadFile(files[0]);
    }
  }, [uploadFile]);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setIsDragOver(false);
  }, []);

  const handleClick = useCallback(() => {
    document.getElementById('pdf-upload').click();
  }, []);

  const handleFileInput = useCallback((e) => {
    const files = e.target.files;
    if (files.length > 0) {
      uploadFile(files[0]);
    }
  }, [uploadFile]);

  const handleDownload = useCallback(() => {
    if (downloadUrl) {
      // Handle both Cloudinary URLs and local API URLs
      if (downloadUrl.startsWith('https://res.cloudinary.com')) {
        // Direct Cloudinary URL - download directly
        window.open(downloadUrl, '_blank');
      } else {
        // Local API URL - use original method
        window.open(downloadUrl, '_blank');
      }
    }
  }, [downloadUrl]);

  const resetUploader = useCallback(() => {
    setIsConverting(false);
    setConversionStatus('');
    setDownloadUrl('');
    setProgress(0);
  }, []);

  return (
    <UploaderContainer>
      {!isConverting && !downloadUrl && (
        <DropZone
          isDragOver={isDragOver}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onClick={handleClick}
        >
          <UploadIcon className="fas fa-file-pdf" />
          <UploadText>Drop PDF file here or click to upload</UploadText>
          <UploadSubtext>Convert PDF to interactive EPUB with selectable text</UploadSubtext>
          <HiddenInput
            id="pdf-upload"
            type="file"
            accept=".pdf"
            onChange={handleFileInput}
          />
        </DropZone>
      )}

      {(isConverting || downloadUrl) && (
        <ConversionStatus>
          {isConverting && (
            <>
              <div>{conversionStatus}</div>
              <ProgressBar>
                <ProgressFill progress={progress} />
              </ProgressBar>
              <div>{progress}%</div>
            </>
          )}

          {downloadUrl && (
            <>
              <div style={{ marginBottom: '1rem' }}>
                <i className="fas fa-check-circle" style={{ color: '#4ade80', marginRight: '0.5rem' }}></i>
                EPUB generated successfully!
              </div>
              <DownloadButton onClick={handleDownload}>
                <i className="fas fa-download" style={{ marginRight: '0.5rem' }}></i>
                Download EPUB
              </DownloadButton>
              <div style={{ marginTop: '1rem' }}>
                <button
                  onClick={resetUploader}
                  style={{
                    background: 'transparent',
                    border: '1px solid rgba(255, 255, 255, 0.3)',
                    color: 'white',
                    padding: '0.5rem 1rem',
                    borderRadius: '0.25rem',
                    cursor: 'pointer'
                  }}
                >
                  Convert Another PDF
                </button>
              </div>
            </>
          )}
        </ConversionStatus>
      )}
    </UploaderContainer>
  );
};

export default PdfUploader; 