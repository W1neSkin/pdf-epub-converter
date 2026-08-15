import React, { useCallback, useEffect, useRef, useState } from 'react';
import styled from 'styled-components';
import { API_BASE_URL, MAX_PDF_MB, MAX_PDF_PAGES } from '../config';
import { getPdfInfo } from '../pdfInfo';

const Wrapper = styled.section`
  width: 100%;
  max-width: 760px;
  margin: 0 auto;
`;

const HeaderRow = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.85rem;
`;

const BackButton = styled.button`
  border: 1px solid rgba(255, 255, 255, 0.25);
  border-radius: 0.6rem;
  background: rgba(255, 255, 255, 0.08);
  color: white;
  padding: 0.7rem 0.95rem;
  cursor: pointer;
  font-weight: 600;
`;

const Card = styled.div`
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-radius: 1rem;
  background: rgba(255, 255, 255, 0.08);
  padding: clamp(1rem, 2vw, 1.5rem);
`;

const DropZone = styled.div`
  border: 2px dashed ${(props) => (props.$active ? '#facc15' : 'rgba(255, 255, 255, 0.35)')};
  border-radius: 0.9rem;
  padding: 2rem 1rem;
  text-align: center;
  transition: border-color 0.2s ease, background 0.2s ease;
  background: ${(props) => (props.$active ? 'rgba(250, 204, 21, 0.12)' : 'rgba(255, 255, 255, 0.03)')};
`;

const Icon = styled.i`
  font-size: 2.6rem;
  color: #facc15;
  margin-bottom: 0.7rem;
`;

const MainText = styled.div`
  font-size: 1.1rem;
  margin-bottom: 0.35rem;
`;

const SubText = styled.div`
  color: rgba(255, 255, 255, 0.78);
  line-height: 1.5;
`;

const Info = styled.div`
  margin-top: 0.9rem;
  color: rgba(255, 255, 255, 0.85);
  font-size: 0.92rem;
`;

const ErrorText = styled.div`
  margin-top: 0.85rem;
  color: #fecaca;
`;

const HiddenInput = styled.input`
  display: none;
`;

const PrimaryButton = styled.button`
  margin-top: 1rem;
  border: none;
  border-radius: 0.65rem;
  background: #facc15;
  color: #111827;
  font-weight: 700;
  min-height: 2.8rem;
  padding: 0.45rem 1.1rem;
  cursor: pointer;
`;

const GhostButton = styled.button`
  border: 1px solid rgba(255, 255, 255, 0.28);
  border-radius: 0.65rem;
  background: transparent;
  color: white;
  min-height: 2.8rem;
  padding: 0.45rem 1rem;
  cursor: pointer;
  font-weight: 600;
`;

const ButtonsRow = styled.div`
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 0.65rem;
  margin-top: 1rem;
`;

const ProgressBar = styled.div`
  height: 0.45rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.2);
  overflow: hidden;
  margin: 0.85rem 0 0.35rem;
`;

const ProgressFill = styled.div`
  height: 100%;
  width: ${(props) => props.$value}%;
  background: linear-gradient(90deg, #facc15, #fde047);
  transition: width 0.25s ease;
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

  const cancelUpload = useCallback((showMessage = true) => {
    cancelledRef.current = true;
    if (abortRef.current) {
      abortRef.current.abort();
    }
    setIsConverting(false);
    setProgress(0);
    setConversionStatus('');
    if (showMessage) {
      setLimitError('Upload cancelled.');
    }
  }, []);

  const uploadFile = useCallback(async (file) => {
    if (!file) return;

    const uploadKey = `${file.name}:${file.size}:${file.lastModified}`;
    const now = Date.now();
    if (lastUpload.current.key === uploadKey && now - lastUpload.current.at < 1500) {
      return;
    }
    lastUpload.current = { key: uploadKey, at: now };

    setLimitError('');
    setFileInfo(null);

    const isPdf = file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf');
    if (!isPdf) {
      setLimitError('Please choose a PDF file.');
      return;
    }

    const sizeMb = file.size / (1024 * 1024);
    if (sizeMb > MAX_PDF_MB) {
      setLimitError(`This file is ${sizeMb.toFixed(1)} MB. Maximum is ${MAX_PDF_MB} MB.`);
      return;
    }

    let info;
    try {
      info = await getPdfInfo(file);
    } catch (error) {
      setLimitError('Could not read this PDF. Try another file.');
      return;
    }

    setFileInfo(info);
    if (info.pages > MAX_PDF_PAGES) {
      setLimitError(`This PDF has ${info.pages} pages. Maximum is ${MAX_PDF_PAGES}.`);
      return;
    }
    if (!user?.token) {
      setLimitError('Please log in first.');
      return;
    }

    cancelledRef.current = false;
    abortRef.current = new AbortController();
    const { signal } = abortRef.current;

    setDownloadUrl('');
    setIsConverting(true);
    setProgress(0);
    setConversionStatus('Starting converter...');

    try {
      if (onEpubGenerated) {
        onEpubGenerated(null);
      }

      // Warmup ping. Even if it fails, we still try one real upload.
      try {
        await fetch(`${API_BASE_URL}/converter/health`, { signal });
      } catch (error) {
        if (error.name === 'AbortError' || cancelledRef.current) {
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
        headers: { Authorization: `Bearer ${user.token}` },
        body: upload,
        signal,
      });

      if (!response.ok) {
        let serverMessage = '';
        try {
          const body = await response.json();
          serverMessage = body.message || body.detail || '';
        } catch (parseError) {
          serverMessage = '';
        }
        throw new Error(serverMessage || `Could not convert this file (${response.status})`);
      }

      const result = await response.json();
      if (!result.success || !result.conversion_id) {
        throw new Error(result.message || 'Conversion failed');
      }

      setProgress(5);
      setConversionStatus('Uploaded. Conversion started...');

      const pollStatus = async (conversionId, attempt) => {
        if (cancelledRef.current) return;

        const statusResponse = await fetch(`${API_BASE_URL}/api/status/${conversionId}`, {
          headers: { Authorization: `Bearer ${user.token}` },
          signal,
        });

        if (!statusResponse.ok) {
          if ([429, 502, 503].includes(statusResponse.status)) {
            setConversionStatus('Server is busy. Checking again...');
            setTimeout(() => pollStatus(conversionId, attempt + 1), 5000);
            return;
          }
          if (statusResponse.status === 404 && attempt < 4) {
            setConversionStatus('Job was restarting. Checking again...');
            setTimeout(() => pollStatus(conversionId, attempt + 1), 3000);
            return;
          }
          throw new Error(`Status check failed: ${statusResponse.status}`);
        }

        const statusData = await statusResponse.json();
        if (statusData.message) {
          setConversionStatus(statusData.message);
        }
        if (typeof statusData.progress === 'number') {
          setProgress((current) => Math.max(current, statusData.progress));
        }

        if (statusData.status === 'completed' && statusData.download_url) {
          setDownloadUrl(statusData.download_url);
          setIsConverting(false);
          setProgress(100);
          setConversionStatus('Conversion completed successfully.');
          if (onEpubGenerated) {
            onEpubGenerated(statusData.download_url);
          }
          return;
        }

        if (statusData.status === 'failed') {
          throw new Error(statusData.message || 'Conversion failed.');
        }

        if (attempt >= 300) {
          throw new Error('Conversion timed out. Try again.');
        }
        setTimeout(() => pollStatus(conversionId, attempt + 1), 3500);
      };

      await pollStatus(result.conversion_id, 1);
    } catch (error) {
      if (cancelledRef.current || error.name === 'AbortError') {
        return;
      }
      console.error(error);
      setIsConverting(false);
      setProgress(0);
      setConversionStatus('');
      setLimitError(error.message || 'Conversion failed.');
      lastUpload.current = { key: '', at: 0 };
    }
  }, [onEpubGenerated, user]);

  useEffect(() => {
    const preventBrowserDrop = (event) => {
      event.preventDefault();
      if (event.dataTransfer) {
        event.dataTransfer.dropEffect = 'copy';
      }
    };
    document.addEventListener('dragenter', preventBrowserDrop, true);
    document.addEventListener('dragover', preventBrowserDrop, true);
    document.addEventListener('drop', preventBrowserDrop, true);
    return () => {
      document.removeEventListener('dragenter', preventBrowserDrop, true);
      document.removeEventListener('dragover', preventBrowserDrop, true);
      document.removeEventListener('drop', preventBrowserDrop, true);
    };
  }, []);

  const handleDragEnter = useCallback((event) => {
    event.preventDefault();
    event.stopPropagation();
    dragDepth.current += 1;
    setIsDragOver(true);
  }, []);

  const handleDragOver = useCallback((event) => {
    event.preventDefault();
    event.stopPropagation();
  }, []);

  const handleDragLeave = useCallback((event) => {
    event.preventDefault();
    event.stopPropagation();
    dragDepth.current -= 1;
    if (dragDepth.current <= 0) {
      dragDepth.current = 0;
      setIsDragOver(false);
    }
  }, []);

  const handleDrop = useCallback((event) => {
    event.preventDefault();
    event.stopPropagation();
    dragDepth.current = 0;
    setIsDragOver(false);
    const file = event.dataTransfer?.files?.[0];
    if (file) {
      uploadFile(file);
    }
  }, [uploadFile]);

  const handleFileInput = useCallback((event) => {
    const file = event.target.files?.[0];
    if (file) {
      uploadFile(file);
      event.target.value = '';
    }
  }, [uploadFile]);

  const openFilePicker = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleDownload = useCallback(async () => {
    if (!downloadUrl) return;

    const path = downloadUrl.startsWith('http')
      ? downloadUrl
      : `${API_BASE_URL}${downloadUrl.startsWith('/') ? downloadUrl : `/${downloadUrl}`}`;

    const response = await fetch(path, {
      headers: { Authorization: `Bearer ${user?.token || ''}` },
    });
    if (!response.ok) {
      setLimitError('Could not download this EPUB. Convert again.');
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

  return (
    <Wrapper>
      <HeaderRow>
        <h2 style={{ fontSize: '1.25rem' }}>Convert PDF to EPUB</h2>
        {onBack && (
          <BackButton type="button" onClick={onBack}>
            <i className="fas fa-arrow-left" style={{ marginRight: '0.45rem' }}></i>
            Library
          </BackButton>
        )}
      </HeaderRow>

      {!isConverting && !downloadUrl && (
        <Card>
          <DropZone
            $active={isDragOver}
            onDragEnter={handleDragEnter}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <Icon className="fas fa-file-pdf" aria-hidden="true"></Icon>
            <MainText>Drop a PDF here</MainText>
            <SubText>Free plan: up to {MAX_PDF_MB} MB and {MAX_PDF_PAGES} pages.</SubText>

            {fileInfo && (
              <Info>
                {fileInfo.name}: {fileInfo.pages} pages, {fileInfo.sizeMb.toFixed(1)} MB
                {fileInfo.title ? ` — ${fileInfo.title}` : ''}
              </Info>
            )}
            {limitError && <ErrorText>{limitError}</ErrorText>}

            <PrimaryButton type="button" onClick={openFilePicker}>
              Choose PDF
            </PrimaryButton>
            <HiddenInput
              ref={fileInputRef}
              type="file"
              accept=".pdf,application/pdf"
              onChange={handleFileInput}
            />
          </DropZone>
        </Card>
      )}

      {isConverting && (
        <Card>
          <div>{conversionStatus || 'Working...'}</div>
          <ProgressBar>
            <ProgressFill $value={progress} />
          </ProgressBar>
          <div>{progress}%</div>
          <ButtonsRow>
            <GhostButton type="button" onClick={() => cancelUpload(true)}>
              Cancel
            </GhostButton>
          </ButtonsRow>
        </Card>
      )}

      {downloadUrl && !isConverting && (
        <Card>
          <div style={{ fontSize: '1.12rem', fontWeight: 700 }}>
            <i className="fas fa-check-circle" style={{ color: '#4ade80', marginRight: '0.55rem' }}></i>
            EPUB generated successfully
          </div>
          <ButtonsRow>
            <PrimaryButton type="button" onClick={handleDownload}>
              Download EPUB
            </PrimaryButton>
            <GhostButton
              type="button"
              onClick={() => {
                setDownloadUrl('');
                setProgress(0);
                setConversionStatus('');
              }}
            >
              Convert another PDF
            </GhostButton>
            {onBack && (
              <GhostButton type="button" onClick={onBack}>
                Back to library
              </GhostButton>
            )}
          </ButtonsRow>
        </Card>
      )}
    </Wrapper>
  );
};

export default PdfUploader;
