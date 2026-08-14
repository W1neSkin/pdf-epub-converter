import React, { useState, useCallback } from 'react';
import styled from 'styled-components';
import { API_BASE_URL, MAX_PDF_MB, MAX_PDF_PAGES, countPdfPages } from '../config';

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

const LimitsNote = styled.div`
  margin-top: 1rem;
  color: rgba(255, 255, 255, 0.9);
  font-size: 0.95rem;
  line-height: 1.5;
`;

const LimitError = styled.div`
  margin-top: 0.75rem;
  color: #fecaca;
  font-size: 0.95rem;
  line-height: 1.4;
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
  const [limitError, setLimitError] = useState('');

  const uploadFile = useCallback(async (file) => {
    setLimitError('');
    const isPdf = file && (
      file.type === 'application/pdf' ||
      file.name.toLowerCase().endsWith('.pdf')
    );
    if (!isPdf) {
      setLimitError('Please choose a PDF file.');
      return;
    }

    const sizeMb = file.size / (1024 * 1024);
    if (sizeMb > MAX_PDF_MB) {
      setLimitError(
        `This file is ${sizeMb.toFixed(1)} MB. Maximum is ${MAX_PDF_MB} MB.`
      );
      return;
    }

    // Count pages locally so a 300+ page book is rejected before the upload.
    const pageCount = await countPdfPages(file);
    if (pageCount > MAX_PDF_PAGES) {
      setLimitError(
        `This PDF has ${pageCount} pages. Maximum is ${MAX_PDF_PAGES} pages.`
      );
      return;
    }

    if (!user?.token) {
      setLimitError('Please log in first.');
      return;
    }

    setIsConverting(true);
    setDownloadUrl('');
    setConversionStatus('Uploading PDF...');
    setProgress(0);

    try {
      if (onEpubGenerated) {
        onEpubGenerated(null);
      }

      const headers = {};
      if (user?.token) {
        headers['Authorization'] = `Bearer ${user.token}`;
      }

      // Free Render can drop the first request. Retry instead of a raw NetworkError.
      const sendConvert = () => {
        const upload = new FormData();
        upload.append('file', file);
        return fetch(`${API_BASE_URL}/api/convert`, {
          method: 'POST',
          headers,
          body: upload,
        });
      };
      const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
      const isWaking = (status) => status === 502 || status === 503 || status === 504;
      const isNetworkError = (err) => {
        const text = String(err && err.message ? err.message : err).toLowerCase();
        return (
          text.includes('networkerror') ||
          text.includes('failed to fetch') ||
          text.includes('network request failed') ||
          text.includes('load failed')
        );
      };

      let response = null;
      for (let wakeTry = 1; wakeTry <= 4; wakeTry += 1) {
        try {
          response = await sendConvert();
          if (!isWaking(response.status)) {
            break;
          }
          if (wakeTry === 4) {
            throw new Error('The converter is still starting. Wait a minute and try again.');
          }
          setConversionStatus('Server is starting. Please wait...');
          setProgress(0);
          await sleep(5000);
        } catch (err) {
          if (err.message && err.message.includes('still starting')) {
            throw err;
          }
          if (!isNetworkError(err) || wakeTry === 4) {
            throw new Error(
              isNetworkError(err)
                ? 'Could not reach the converter. Wait a minute and try again.'
                : err.message
            );
          }
          setConversionStatus('Connection lost. Trying again...');
          setProgress(0);
          await sleep(5000);
        }
      }

      if (!response.ok) {
        if (isWaking(response.status)) {
          throw new Error('The converter is still starting. Wait a minute and try again.');
        }
        let serverMessage = '';
        try {
          const errBody = await response.json();
          serverMessage = errBody.message || errBody.detail || '';
        } catch (parseError) {
          serverMessage = '';
        }
        throw new Error(serverMessage || `Could not convert this file (${response.status})`);
      }

      const result = await response.json();

      if (!result.success || !result.conversion_id) {
        throw new Error(result.message || 'Conversion failed');
      }

      // Upload is done. From here the bar follows the server, not fake percents.
      setConversionStatus('Uploaded. Conversion started...');
      setProgress(5);

      // Convert now returns immediately. Poll until the background job finishes.
      const maxAttempts = 150;
      const pollStatus = async (conversionId, attempt) => {
        const statusHeaders = { Authorization: `Bearer ${user.token}` };
        const statusResponse = await fetch(`${API_BASE_URL}/api/status/${conversionId}`, {
          headers: statusHeaders
        });
        if (!statusResponse.ok) {
          if (statusResponse.status === 502 || statusResponse.status === 503) {
            throw new Error('The converter is still starting. Wait a minute and try again.');
          }
          throw new Error(`Status check failed: ${statusResponse.status}`);
        }
        const statusData = await statusResponse.json();

        if (statusData.message) {
          setConversionStatus(statusData.message);
        }
        if (typeof statusData.progress === 'number') {
          // Never jump backwards. The old UI leapt to 40% before work started.
          setProgress((current) => Math.max(current, statusData.progress));
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
            setConversionStatus(pollError.message);
            setProgress(0);
            setTimeout(() => {
              setIsConverting(false);
              setConversionStatus('');
            }, 8000);
          });
        }, 2000);
      };

      await pollStatus(result.conversion_id, 1);
    } catch (error) {
      console.error('Upload error:', error);
      setConversionStatus(error.message);
      setProgress(0);
      // Keep the message long enough to read. Do not flash a raw 502.
      setTimeout(() => {
        setIsConverting(false);
        setConversionStatus('');
      }, 8000);
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
          <UploadSubtext>Convert a PDF to EPUB with selectable text</UploadSubtext>
          <LimitsNote>
            Free plan: up to {MAX_PDF_MB} MB and {MAX_PDF_PAGES} pages.
            A paid plan can raise these limits later.
          </LimitsNote>
          {limitError && <LimitError>{limitError}</LimitError>}
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