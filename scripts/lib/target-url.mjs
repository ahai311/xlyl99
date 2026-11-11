/** Target URL helpers for redirect shell + Android string resources */

export function normalizeTargetUrl(raw, fallback = 'https://example.com/') {
  let u = String(raw || fallback).trim();
  if (!/^https?:\/\//i.test(u)) u = `https://${u}`;
  const parsed = new URL(u);
  if (!['http:', 'https:'].includes(parsed.protocol) || parsed.username || parsed.password) {
    throw new Error('Target URL must be an HTTP/HTTPS website without credentials');
  }
  return parsed.href;
}

export function targetWithNativeParam(url) {
  const u = new URL(normalizeTargetUrl(url));
  u.searchParams.set('native', '1');
  return u.href;
}

export function hostFromTargetUrl(url) {
  try {
    return new URL(normalizeTargetUrl(url)).hostname.toLowerCase();
  } catch {
    return '';
  }
}
