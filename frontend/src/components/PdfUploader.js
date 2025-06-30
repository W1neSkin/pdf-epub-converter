import React, { useState, useCallback } from 'react';
import styled from 'styled-components';

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

const API_BASE_URL = process.env.REACT_APP_API_URL || 'https://pdf-converter-api-gateway.onrender.com';

const PdfUploader = ({ onEpubGenerated, onBack, user }) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const [isConverting, setIsConverting] = useState(false);
  const [conversionStatus, setConversionStatus] = useState('');
  const [downloadUrl, setDownloadUrl] = useState('');
  const [progress, setProgress] = useState(0);

  const uploadFile = useCallback(async (file) => {
    if (!file || !file.type === 'application/pdf') {
      alert('Please select a valid PDF file');
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
      
      if (result.success) {
        setConversionStatus('Generating EPUB...');
        setProgress(70);

        if (result.download_url) {
          // Direct download URL provided
          setDownloadUrl(result.download_url);
          setConversionStatus('Conversion completed successfully!');
          setProgress(100);
          
          if (onEpubGenerated) {
            onEpubGenerated(result.download_url);
          }
        } else {
          // Fallback to polling if no direct URL provided
          const pollStatus = async (conversionId) => {
            const statusHeaders = {};
            if (user?.token) {
              statusHeaders['Authorization'] = `Bearer ${user.token}`;
            }
            
            const statusResponse = await fetch(`${API_BASE_URL}/api/status/${conversionId}`, {
              headers: statusHeaders
            });
            const statusData = await statusResponse.json();

            if (statusData.status === 'completed' && statusData.download_url) {
              setDownloadUrl(statusData.download_url);
              setConversionStatus('Conversion completed successfully!');
              setProgress(100);
              
              if (onEpubGenerated) {
                onEpubGenerated(statusData.download_url);
              }
            } else if (statusData.status === 'failed') {
              throw new Error('Conversion failed on server');
            } else {
              // Still processing, poll again
              setTimeout(() => pollStatus(conversionId), 2000);
            }
          };

          if (result.conversion_id) {
            pollStatus(result.conversion_id);
          } else {
            throw new Error('No conversion ID provided');
          }
        }
      } else {
        throw new Error(result.message || 'Conversion failed');
      }
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