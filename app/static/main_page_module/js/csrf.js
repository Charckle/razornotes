function csrfHeaders(extra) {
  const headers = Object.assign({}, extra || {});
  const token = document.querySelector('meta[name="csrf-token"]')?.content;
  if (token) headers['X-CSRFToken'] = token;
  return headers;
}

function setCsrfToken(token) {
  const meta = document.querySelector('meta[name="csrf-token"]');
  if (meta) meta.content = token;
}

async function refreshCsrfToken() {
  const url = document.querySelector('meta[name="csrf-refresh-url"]')?.content || '/csrf-token/';
  const r = await fetch(url, { method: 'GET', credentials: 'same-origin' });
  if (!r.ok) throw new Error('Could not refresh CSRF token');
  const data = await r.json();
  setCsrfToken(data.csrf_token);
  return data.csrf_token;
}

async function isCsrfFailure(response) {
  if (response.status !== 400) return false;
  try {
    const text = await response.clone().text();
    return /csrf/i.test(text);
  } catch (_) {
    return true;
  }
}

async function fetchWithCsrf(url, options, retried) {
  options = options || {};
  retried = !!retried;
  const opts = Object.assign({}, options, {
    credentials: options.credentials || 'same-origin',
    headers: csrfHeaders(options.headers)
  });
  const r = await fetch(url, opts);
  if (!retried && await isCsrfFailure(r)) {
    await refreshCsrfToken();
    return fetchWithCsrf(url, options, true);
  }
  return r;
}
