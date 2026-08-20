import React, { useCallback, useEffect, useRef, useState } from 'react';
import styled from 'styled-components';
import { CONVERTER_BASE_URL, MAX_PDF_MB, MAX_PDF_PAGES } from '../config';
import { getPdfInfo } from '../pdfInfo';
import ConversionModePicker from './ConversionModePicker';
import {
  ButtonRow,
  DropArea as DropZone,
  Panel as Card,
  PrimaryAction as PrimaryButton,
  SecondaryAction as GhostButton,
} from './ui';

const Wrapper = styled.section`
  width: 100%;
  max-width: 760px;
  margin: 0 auto;
`;

const HeaderRow = styled.div`
  margin-bottom: 1rem;
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

const Actions = styled(ButtonRow)`
  justify-content: center;
  margin-top: 1rem;
`;

const DownloadGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: 0.7rem;
  margin-top: 1rem;
`;

const DownloadOption = styled.div`
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 0.75rem;
  padding: 0.85rem;
  background: rgba(15, 23, 42, 0.35);

  p {
    margin: 0.35rem 0 0.75rem;
    min-height: 2.7rem;
    color: rgba(255, 255, 255, 0.68);
    font-size: 0.84rem;
    line-height: 1.4;
  }

  button {
    width: 100%;
  }
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

const resolveConverterUrl = (fileUrl) => (
  fileUrl.startsWith('http')
    ? fileUrl
    : `${CONVERTER_BASE_URL}${fileUrl.startsWith('/') ? fileUrl : `/${fileUrl}`}`
);

const PdfUploader = ({ onEpubGenerated, onBack, onSessionExpired, user }) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const [isConverting, setIsConverting] = useState(false);
  const [conversionStatus, setConversionStatus] = useState('');
  const [downloadUrl, setDownloadUrl] = useState('');
  const [tablesDownloadUrl, setTablesDownloadUrl] = useState('');
  const [archiveDownloadUrl, setArchiveDownloadUrl] = useState('');
  const [progress, setProgress] = useState(0);
  const [limitError, setLimitError] = useState('');
  const [fileInfo, setFileInfo] = useState(null);
  const [selectedAction, setSelectedAction] = useState('epub');
  const [jobType, setJobType] = useState('epub');
  const [downloadName, setDownloadName] = useState('converted.epub');
  const [tablesDownloadName, setTablesDownloadName] = useState('tables.csv');
  const [archiveDownloadName, setArchiveDownloadName] = useState('separate_tables.zip');
  const [csvStats, setCsvStats] = useState({
    documentRowCount: 0,
    tableCount: 0,
    rowCount: 0,
  });

  const dragDepth = useRef(0);
  const fileInputRef = useRef(null);
  const lastUpload = useRef({ key: '', at: 0 });
  const cancelledRef = useRef(false);
  const abortRef = useRef(null);
  const actionRef = useRef('epub');
  const AUTH_EXPIRED = 'AUTH_EXPIRED';

  const waitWithAbort = useCallback((ms, signal) => {
    return new Promise((resolve, reject) => {
      if (signal?.aborted) {
        const err = new Error('aborted');
        err.name = 'AbortError';
        reject(err);
        return;
      }
      let onAbort = null;
      const timeoutId = setTimeout(() => {
        if (signal && onAbort) {
          signal.removeEventListener('abort', onAbort);
        }
        resolve();
      }, ms);
      onAbort = () => {
        clearTimeout(timeoutId);
        if (signal) {
          signal.removeEventListener('abort', onAbort);
        }
        const err = new Error('aborted');
        err.name = 'AbortError';
        reject(err);
      };
      if (signal) {
        signal.addEventListener('abort', onAbort, { once: true });
      }
    });
  }, []);

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

  const uploadFile = useCallback(async (file, action = 'epub') => {
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
    setTablesDownloadUrl('');
    setArchiveDownloadUrl('');
    setIsConverting(true);
    setProgress(0);
    setCsvStats({ documentRowCount: 0, tableCount: 0, rowCount: 0 });
    setJobType(action);
    setDownloadName(action === 'csv' ? 'document.xlsx' : 'converted.epub');
    setTablesDownloadName('tables.csv');
    setArchiveDownloadName('separate_tables.zip');
    setConversionStatus(action === 'csv' ? 'Starting document extractor...' : 'Starting converter...');

    try {
      // 429 is mostly handled by API Gateway now; keep only one client retry for wake-up edge cases.
      const retryableStatuses = new Set([502, 503, 504]);

      setConversionStatus(action === 'csv' ? 'Uploading PDF for Excel export...' : 'Uploading PDF...');
      const upload = new FormData();
      upload.append('file', file);
      const endpoint = action === 'csv' ? '/api/extract-tables' : '/api/convert';
      const uploadAttempts = 2;
      let response = null;
      for (let uploadTry = 1; uploadTry <= uploadAttempts; uploadTry += 1) {
        try {
          response = await fetch(`${CONVERTER_BASE_URL}${endpoint}`, {
            method: 'POST',
            headers: { Authorization: `Bearer ${user.token}` },
            body: upload,
            signal,
          });
        } catch (error) {
          if (error.name === 'AbortError' || cancelledRef.current) {
            return;
          }
          const canRetry = uploadTry < uploadAttempts;
          if (!canRetry) {
            throw error;
          }
          setConversionStatus('Network issue. Retrying upload...');
          await waitWithAbort(4000, signal);
          continue;
        }

        if (response.ok) {
          break;
        }

        if (response.status === 401) {
          throw new Error(AUTH_EXPIRED);
        }

        const isWakeLimit = response.status === 429;
        const canRetry =
          ((isWakeLimit && uploadTry === 1) || retryableStatuses.has(response.status)) &&
          uploadTry < uploadAttempts;
        if (canRetry) {
          setConversionStatus(
            isWakeLimit
              ? 'Server is still waking up. Trying once more...'
              : 'Server is waking up. Please wait...'
          );
          await waitWithAbort(isWakeLimit ? 12000 : 4000, signal);
          continue;
        }

        let serverMessage = '';
        try {
          const body = await response.json();
          serverMessage = body.message || body.detail || '';
        } catch (parseError) {
          serverMessage = '';
        }
        if (!serverMessage && response.status === 429) {
          serverMessage = 'Server is still waking up. Please retry in about a minute.';
        }
        throw new Error(serverMessage || `Could not convert this file (${response.status})`);
      }

      if (!response || !response.ok) {
        throw new Error('Could not upload this file.');
      }

      const result = await response.json();
      if (!result.success || !result.conversion_id) {
        throw new Error(result.message || 'Request failed');
      }

      setProgress(5);
      setConversionStatus(action === 'csv' ? 'Uploaded. Extracting text and tables...' : 'Uploaded. Conversion started...');

      const pollStatus = async (conversionId) => {
        for (let attempt = 1; attempt <= 300; attempt += 1) {
          if (cancelledRef.current) return;

          let statusResponse;
          try {
            statusResponse = await fetch(`${CONVERTER_BASE_URL}/api/status/${conversionId}`, {
              headers: { Authorization: `Bearer ${user.token}` },
              signal,
            });
          } catch (error) {
            if (error.name === 'AbortError' || cancelledRef.current) {
              throw error;
            }
            setConversionStatus('Network issue. Checking conversion again...');
            await waitWithAbort(3500, signal);
            continue;
          }

          if (!statusResponse.ok) {
            if (statusResponse.status === 401) {
              throw new Error(AUTH_EXPIRED);
            }
            if ([429, 502, 503, 504].includes(statusResponse.status)) {
              setConversionStatus('Server is busy. Checking again...');
              await waitWithAbort(5000, signal);
              continue;
            }
            if (statusResponse.status === 404 && attempt < 4) {
              setConversionStatus('Job was restarting. Checking again...');
              await waitWithAbort(3000, signal);
              continue;
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
            const outputKind = statusData.output_kind || action;
            setJobType(outputKind);
            setDownloadName(
              statusData.download_name ||
              (outputKind === 'xlsx' || outputKind === 'csv'
                ? 'document.xlsx'
                : 'converted.epub')
            );
            setTablesDownloadUrl(statusData.tables_download_url || '');
            setTablesDownloadName(
              statusData.tables_download_name || 'tables.csv'
            );
            setArchiveDownloadUrl(statusData.archive_download_url || '');
            setArchiveDownloadName(
              statusData.archive_download_name || 'separate_tables.zip'
            );
            setConversionStatus(
              outputKind === 'xlsx' || outputKind === 'csv'
                ? 'Excel document generated successfully.'
                : 'Conversion completed successfully.'
            );
            if (outputKind === 'xlsx' || outputKind === 'csv') {
              setCsvStats({
                documentRowCount: Number(statusData.document_row_count || 0),
                tableCount: Number(statusData.table_count || 0),
                rowCount: Number(statusData.row_count || 0),
              });
            }
            return;
          }

          if (statusData.status === 'failed') {
            throw new Error(statusData.message || 'Conversion failed.');
          }

          await waitWithAbort(3500, signal);
        }
        throw new Error('Conversion timed out. Try again.');
      };

      await pollStatus(result.conversion_id);
    } catch (error) {
      if (cancelledRef.current || error.name === 'AbortError') {
        return;
      }
      if (error.message === AUTH_EXPIRED) {
        cancelUpload(false);
        setLimitError('Session expired. Please log in again.');
        if (onSessionExpired) {
          onSessionExpired();
        }
        return;
      }
      console.error(error);
      setIsConverting(false);
      setProgress(0);
      setConversionStatus('');
      setLimitError(error.message || 'Conversion failed.');
      lastUpload.current = { key: '', at: 0 };
    }
  }, [cancelUpload, onSessionExpired, user, waitWithAbort]);

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
      uploadFile(file, actionRef.current);
    }
  }, [uploadFile]);

  const handleFileInput = useCallback((event) => {
    const file = event.target.files?.[0];
    if (file) {
      uploadFile(file, actionRef.current);
      event.target.value = '';
    }
  }, [uploadFile]);

  const openFilePicker = useCallback((action) => {
    actionRef.current = action;
    setSelectedAction(action);
    fileInputRef.current?.click();
  }, []);

  const downloadFile = useCallback(async (fileUrl, fileName) => {
    if (!fileUrl) return;

    const path = resolveConverterUrl(fileUrl);

    const response = await fetch(path, {
      headers: { Authorization: `Bearer ${user?.token || ''}` },
    });
    if (!response.ok) {
      if (response.status === 401) {
        setLimitError('Session expired. Please log in again.');
        if (onSessionExpired) {
          onSessionExpired();
        }
        return;
      }
      setLimitError('Could not download this file. Try again.');
      return;
    }

    const blob = await response.blob();
    const objectUrl = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = objectUrl;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(objectUrl);
  }, [onSessionExpired, user]);

  const isDocumentExport = jobType === 'xlsx' || jobType === 'csv';
  const resetConversion = () => {
    setDownloadUrl('');
    setTablesDownloadUrl('');
    setArchiveDownloadUrl('');
    setProgress(0);
    setConversionStatus('');
    setDownloadName('converted.epub');
    setTablesDownloadName('tables.csv');
    setArchiveDownloadName('separate_tables.zip');
    setJobType('epub');
    setCsvStats({ documentRowCount: 0, tableCount: 0, rowCount: 0 });
  };

  return (
    <Wrapper>
      <HeaderRow>
        <h2 style={{ fontSize: '1.45rem', marginBottom: '0.35rem' }}>
          Convert or export PDF
        </h2>
        <SubText>First choose the result. Then upload one PDF file.</SubText>
      </HeaderRow>

      {!isConverting && !downloadUrl && (
        <Card>
          <ConversionModePicker
            value={selectedAction}
            onChange={(action) => {
              setSelectedAction(action);
              actionRef.current = action;
              setLimitError('');
            }}
          />
          <DropZone
            $active={isDragOver}
            onDragEnter={handleDragEnter}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <Icon className="fas fa-file-pdf" aria-hidden="true"></Icon>
            <MainText>Drop a PDF here</MainText>
            <SubText>
              {selectedAction === 'csv'
                ? 'Creates a readable XLSX workbook and table-only CSV downloads.'
                : 'Creates a fixed-layout EPUB and saves it to your library.'}
              {' '}Up to {MAX_PDF_MB} MB and {MAX_PDF_PAGES} pages.
            </SubText>

            {fileInfo && (
              <Info>
                {fileInfo.name}: {fileInfo.pages} pages, {fileInfo.sizeMb.toFixed(1)} MB
                {fileInfo.title ? ` — ${fileInfo.title}` : ''}
              </Info>
            )}
            {limitError && <ErrorText>{limitError}</ErrorText>}

            <Actions>
              <PrimaryButton
                type="button"
                onClick={() => openFilePicker(selectedAction)}
              >
                Choose PDF
              </PrimaryButton>
            </Actions>
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
          <Actions>
            <GhostButton type="button" onClick={() => cancelUpload(true)}>
              Cancel
            </GhostButton>
          </Actions>
        </Card>
      )}

      {downloadUrl && !isConverting && (
        <Card>
          <div style={{ fontSize: '1.12rem', fontWeight: 700 }}>
            <i className="fas fa-check-circle" style={{ color: '#4ade80', marginRight: '0.55rem' }}></i>
            {isDocumentExport ? 'Excel document generated successfully' : 'EPUB generated successfully'}
          </div>
          {isDocumentExport ? (
            <DownloadGrid>
              <DownloadOption>
                <strong>Workbook</strong>
                <p>Readable text and tables, with one worksheet per PDF page.</p>
                <PrimaryButton
                  type="button"
                  onClick={() => downloadFile(downloadUrl, downloadName)}
                >
                  Download XLSX
                </PrimaryButton>
              </DownloadOption>
              {tablesDownloadUrl && (
                <DownloadOption>
                  <strong>All tables</strong>
                  <p>One CSV file for importing every detected table.</p>
                  <GhostButton
                    type="button"
                    onClick={() => downloadFile(tablesDownloadUrl, tablesDownloadName)}
                  >
                    Download CSV
                  </GhostButton>
                </DownloadOption>
              )}
              {archiveDownloadUrl && (
                <DownloadOption>
                  <strong>Separate tables</strong>
                  <p>A ZIP containing one CSV file for each detected table.</p>
                  <GhostButton
                    type="button"
                    onClick={() => downloadFile(archiveDownloadUrl, archiveDownloadName)}
                  >
                    Download ZIP
                  </GhostButton>
                </DownloadOption>
              )}
            </DownloadGrid>
          ) : (
            <>
              <Info>This EPUB was also saved to your personal library.</Info>
              <Actions>
                <PrimaryButton
                  type="button"
                  onClick={() => (
                    onEpubGenerated && onEpubGenerated(resolveConverterUrl(downloadUrl))
                  )}
                >
                  Open in reader
                </PrimaryButton>
                <GhostButton
                  type="button"
                  onClick={() => downloadFile(downloadUrl, downloadName)}
                >
                  Download EPUB
                </GhostButton>
              </Actions>
            </>
          )}
          {isDocumentExport && (
            <Info>
              Found {csvStats.tableCount} tables and {csvStats.rowCount} table rows.
            </Info>
          )}
          <Actions>
            <GhostButton type="button" onClick={resetConversion}>
              Convert another PDF
            </GhostButton>
            {onBack && (
              <GhostButton type="button" onClick={onBack}>
                Back to library
              </GhostButton>
            )}
          </Actions>
        </Card>
      )}
    </Wrapper>
  );
};

export default PdfUploader;
