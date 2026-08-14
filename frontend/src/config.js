// Single API base URL for all frontend requests.
export const API_BASE_URL =
  process.env.REACT_APP_API_URL || 'https://pdf-converter-api-gateway.onrender.com';

// Keep these in sync with backend/app.py MAX_FILE_SIZE and MAX_PAGES.
export const MAX_PDF_MB = 50;
export const MAX_PDF_PAGES = 400;

// Best-effort page count in the browser so we can reject huge PDFs before upload.
export async function countPdfPages(file) {
  const buffer = await file.arrayBuffer();
  const text = new TextDecoder('latin1').decode(buffer);
  const matches = text.match(/\/Type\s*\/Page(?!s)\b/g);
  return matches ? matches.length : 0;
}
