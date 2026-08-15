import React, { useState, useCallback, useEffect, useRef } from 'react';
import styled from 'styled-components';
import { API_BASE_URL, MAX_PDF_MB, MAX_PDF_PAGES } from '../config';
import { getPdfInfo } from '../pdfInfo';

const UploaderContainer = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2rem;
  max-width: 600px;
  margin: 0 auto;
`;

const DropZone = styled.div`
  border: 3px dashed ${props => props.$isDragOver ? '#ffd700' : 'rgba(255, 255, 255, 0.3)'};
  border-radius: 1rem;
  padding: 3rem;
  text-align: center;
  background: ${props => props.$isDragOver ? 'rgba(255, 215, 0, 0.1)' : 'rgba(255, 255, 255, 0.05)'};
  backdrop-filter: blur(10px);
  transition: all 0.3s ease;
  width: 100%;
  min-height: 280px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  user-select: none;
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

const FileInfo = styled.div`
  margin-top: 0.75rem;
  color: rgba(255, 255, 255, 0.85);
  font-size: 0.9rem;
  line-height: 1.5;
`;

const HiddenInput = styled.input`
  display: none;
`;

const ChooseButton = styled.button`
  margin-top: 1.25rem;
  background: linear-gradient(135deg, #ffd700, #ffed4e);
  color: #333;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 0.5rem;
  font-weight: bold;
  cursor: pointer;
`;

const CancelButton = styled.button`
  margin-top: 1rem;
  background: transparent;
  color: white;
  border: 1px solid rgba(255, 255, 255, 0.4);
  padding: 0.5rem 1.25rem;
  border-radius: 0.5rem;
  cursor: pointer;
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
  const [fileInfo, setFileInfo] = useState(null);
  const dragDepth = useRef(0);
  const fileInputRef = useRef(null);
  const lastUpload = useRef({ key: '', at: 0 });
  const cancelledRef = useRef(false);
  const abortRef = useRef(null);

  const uploadFile = useCallback(async (file) => {
    if (!file) {
      return;
    }
    // Drop can fire twice (zone + window, or drop + file input change).
    const uploadKey = `${file.name}:${file.size}:${file.lastModified}`;
    const now = Date.now();
    if (lastUpload.current.key === uploadKey && now - lastUpload.current.at < 1500) {
      return;
    }
    lastUpload.current = { key: uploadKey, at: now };

    setLimitError('');
    setFileInfo(null);
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

    // Read page count in the browser with pdf-lib. Do not upload yet.
    let info;
    try {
      info = await getPdfInfo(file);
    } catch (readError) {
      setLimitError('Could not read this PDF. Try another file.');
      return;
    }
    setFileInfo(info);
    if (info.pages > MAX_PDF_PAGES) {
      setLimitError(
        `This PDF has ${info.pages} pages. The free plan allows ${MAX_PDF_PAGES} pages.`
      );
      return;
    }

    if (!user?.token) {
      setLimitError('Please log in first.');
      return;
    }

    cancelledRef.current = false;
    abortRef.current = new AbortController();
    const signal = abortRef.current.signal;

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

      // One wake ping, then one upload. No silent retry loop.
      setConversionStatus('Starting the converter...');
      try {
        await fetch(`${API_BASE_URL}/converter/health`, { signal });
      } catch (wakeError) {
        if (wakeError.name === 'AbortError' || cancelledRef.current) {
          return;
        }
      }
      if (cancelledRef.current) {
        return;
      }

      setConversionStatus('Uploading PDF...');
      const upload = new FormData();
      upload.append('file', file);
      const response = await fetch(`${API_BASE_URL}/api/convert`, {
        method: 'POST',
        headers,
        body: upload,
        signal,
      });

      if (!response.ok) {
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
      const maxAttempts = 400;
      const pollStatus = async (conversionId, attempt) => {
        if (cancelledRef.current) {
          return;
        }
        const statusHeaders = { Authorization: `Bearer ${user.token}` };
        const statusResponse = await fetch(`${API_BASE_URL}/api/status/${conversionId}`, {
          headers: statusHeaders,
          signal,
        });
        if (!statusResponse.ok) {
          if (
            statusResponse.status === 429 ||
            statusResponse.status === 502 ||
            statusResponse.status === 503
          ) {
            setConversionStatus('Server is busy. Checking again...');
            setTimeout(() => {
              if (cancelledRef.current) {
                return;
              }
              pollStatus(conversionId, attempt + 1).catch((pollError) => {
                setIsConverting(false);
                setProgress(0);
                setConversionStatus('');
                setLimitError(pollError.message);
              });
            }, 8000);
            return;
          }
          // 404 after progress usually means the host restarted and lost the job.
          if (statusResponse.status === 404 && attempt < 4) {
            setConversionStatus('Lost the conversion job. Checking again...');
            setTimeout(() => {
              if (cancelledRef.current) {
                return;
              }
              pollStatus(conversionId, attempt + 1).catch((pollError) => {
                setIsConverting(false);
                setProgress(0);
                setConversionStatus('');
                setLimitError(pollError.message);
              });
            }, 3000);
            return;
          }
          if (statusResponse.status === 404) {
            throw new Error(
              'Conversion was interrupted. The server ran out of memory or restarted. Please try again.'
            );
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
          if (cancelledRef.current) {
            return;
          }
          pollStatus(conversionId, attempt + 1).catch((pollError) => {
            if (cancelledRef.current || pollError.name === 'AbortError') {
              return;
            }
            console.error('Upload error:', pollError);
            setIsConverting(false);
            setProgress(0);
            setConversionStatus('');
            setLimitError(pollError.message);
          });
        }, 4000);
      };

      await pollStatus(result.conversion_id, 1);
    } catch (error) {
      if (cancelledRef.current || error.name === 'AbortError') {
        return;
      }
      console.error('Upload error:', error);
      lastUpload.current = { key: '', at: 0 };
      setIsConverting(false);
      setProgress(0);
      setConversionStatus('');
      setLimitError(error.message);
    }
  }, [user, onEpubGenerated]);

  const cancelUpload = useCallback(() => {
    cancelledRef.current = true;
    if (abortRef.current) {
      abortRef.current.abort();
    }
    lastUpload.current = { key: '', at: 0 };
    setIsConverting(false);
    setProgress(0);
    setConversionStatus('');
    setDownloadUrl('');
    setLimitError('');
  }, []);

  // Capture-phase listeners beat the browser default (red "blocked" cursor).
  useEffect(() => {
    const allowDrop = (e) => {
      e.preventDefault();
      if (e.dataTransfer) {
        e.dataTransfer.dropEffect = 'copy';
      }
    };
    const onDrop = (e) => {
      // Only block the browser from opening the PDF. Upload is handled by the box.
      e.preventDefault();
    };
    document.addEventListener('dragenter', allowDrop, true);
    document.addEventListener('dragover', allowDrop, true);
    document.addEventListener('drop', onDrop, true);
    return () => {
      document.removeEventListener('dragenter', allowDrop, true);
      document.removeEventListener('dragover', allowDrop, true);
      document.removeEventListener('drop', onDrop, true);
    };
  }, []);

  const handleDragEnter = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    dragDepth.current += 1;
    setIsDragOver(true);
  }, []);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.dataTransfer) {
      e.dataTransfer.dropEffect = 'copy';
    }
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    dragDepth.current -= 1;
    if (dragDepth.current <= 0) {
      dragDepth.current = 0;
      setIsDragOver(false);
    }
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    dragDepth.current = 0;
    setIsDragOver(false);
    const file = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
    if (file) {
      uploadFile(file);
    }
  }, [uploadFile]);

  const handleFileInput = useCallback((e) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      uploadFile(files[0]);
      e.target.value = '';
    }
  }, [uploadFile]);

  const openFilePicker = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  }, []);

  const handleDownload = useCallback(async () => {
    if (!downloadUrl) {
      return;
    }

    // Cloudinary links are public. Relative /api/download/... is not:
    // the browser would open it on GitHub Pages and get a 404.
    if (downloadUrl.startsWith('http') && downloadUrl.includes('cloudinary.com')) {
      window.open(downloadUrl, '_blank');
      return;
    }

    const path = downloadUrl.startsWith('http')
      ? downloadUrl
      : `${API_BASE_URL}${downloadUrl.startsWith('/') ? downloadUrl : `/${downloadUrl}`}`;

    const response = await fetch(path, {
      headers: { Authorization: `Bearer ${user?.token || ''}` },
    });
    if (!response.ok) {
      setLimitError('Could not download the EPUB. Convert the file again.');
      return;
    }
    const blob = await response.blob();
    const objectUrl = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = objectUrl;
    link.download = 'converted.epub';
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(objectUrl);
  }, [downloadUrl, user]);

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
          $isDragOver={isDragOver}
          onDragEnter={handleDragEnter}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <UploadIcon className="fas fa-file-pdf" />
          <UploadText>Drop a PDF here</UploadText>
          <UploadSubtext>Convert a PDF to EPUB with selectable text</UploadSubtext>
          <LimitsNote>
            Free plan: up to {MAX_PDF_MB} MB and {MAX_PDF_PAGES} pages.
            A paid plan can raise these limits later.
          </LimitsNote>
          {fileInfo && (
            <FileInfo>
              {fileInfo.name}: {fileInfo.pages} pages, {fileInfo.sizeMb.toFixed(1)} MB
              {fileInfo.title ? ` — ${fileInfo.title}` : ''}
            </FileInfo>
          )}
          {limitError && <LimitError>{limitError}</LimitError>}
          <ChooseButton type="button" onClick={openFilePicker}>
            Choose PDF
          </ChooseButton>
          <HiddenInput
            ref={fileInputRef}
            type="file"
            accept=".pdf,application/pdf"
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
              <CancelButton type="button" onClick={cancelUpload}>
                Cancel
              </CancelButton>
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