// Single API base URL for all frontend requests.
export const API_BASE_URL =
  process.env.REACT_APP_API_URL || 'https://pdf-converter-api-gateway.onrender.com';

// Auth calls go directly to auth service to avoid extra gateway cold-start hop.
export const AUTH_BASE_URL =
  process.env.REACT_APP_AUTH_URL || 'https://pdf-converter-auth-service.onrender.com';

// Free-plan limits. Keep in sync with backend/plan_limits.py.
// A future paid plan can raise pages and file size when we pay for a bigger host.
export const PLANS = {
  free: { maxPages: 50, maxMb: 50 },
  pro: { maxPages: 2000, maxMb: 200 }
};
export const CURRENT_PLAN = 'free';
export const MAX_PDF_MB = PLANS[CURRENT_PLAN].maxMb;
export const MAX_PDF_PAGES = PLANS[CURRENT_PLAN].maxPages;
