// Single API base URL for all frontend requests.
export const API_BASE_URL =
  process.env.REACT_APP_API_URL || 'https://pdf-converter-api-gateway.onrender.com';

// Free-plan limits. Keep in sync with backend/plan_limits.py.
// A future paid plan can raise pages and file size when we pay for a bigger host.
export const PLANS = {
  free: { maxPages: 400, maxMb: 50 },
  pro: { maxPages: 2000, maxMb: 200 }
};
export const CURRENT_PLAN = 'free';
export const MAX_PDF_MB = PLANS[CURRENT_PLAN].maxMb;
export const MAX_PDF_PAGES = PLANS[CURRENT_PLAN].maxPages;

// Best-effort page count in the browser so we can reject huge PDFs before upload.
export async function countPdfPages(file) {
  const buffer = await file.arrayBuffer();
  const text = new TextDecoder('latin1').decode(buffer);
  const matches = text.match(/\/Type\s*\/Page(?!s)\b/g);
  return matches ? matches.length : 0;
}
