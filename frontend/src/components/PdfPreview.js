import React, { useEffect, useState } from 'react';
import styled from 'styled-components';


const PreviewShell = styled.div`
  min-width: 0;
  border: 1px solid #27324a;
  border-radius: 1rem;
  overflow: hidden;
  background: #080d18;
`;

const PreviewHeader = styled.div`
  min-height: 3rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.7rem 0.9rem;
  border-bottom: 1px solid #27324a;
  background: #121a2d;
  font-size: 0.86rem;
`;

const FileName = styled.strong`
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
`;

const FullPreviewLink = styled.a`
  flex: 0 0 auto;
  color: #f7c948;
  text-decoration: none;
  font-weight: 700;
`;

const Frame = styled.iframe`
  display: block;
  width: 100%;
  height: min(68vh, 680px);
  min-height: 480px;
  border: 0;
  background: #293142;

  @media (max-width: 720px) {
    height: 58vh;
    min-height: 360px;
  }
`;

const Fallback = styled.div`
  min-height: 480px;
  display: grid;
  place-items: center;
  padding: 2rem;
  color: rgba(255, 255, 255, 0.65);
  text-align: center;
`;

const PdfPreview = ({ file }) => {
  const [previewUrl, setPreviewUrl] = useState('');

  useEffect(() => {
    if (!file || typeof URL.createObjectURL !== 'function') return undefined;
    const objectUrl = URL.createObjectURL(file);
    setPreviewUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [file]);

  return (
    <PreviewShell>
      <PreviewHeader>
        <FileName title={file?.name}>{file?.name || 'PDF preview'}</FileName>
        {previewUrl && (
          <FullPreviewLink href={previewUrl} target="_blank" rel="noreferrer">
            Open full preview
          </FullPreviewLink>
        )}
      </PreviewHeader>
      {previewUrl ? (
        <Frame
          title="PDF preview"
          src={`${previewUrl}#page=1&view=FitH&navpanes=0`}
        />
      ) : (
        <Fallback>Preview is not available in this browser.</Fallback>
      )}
    </PreviewShell>
  );
};

export default PdfPreview;
