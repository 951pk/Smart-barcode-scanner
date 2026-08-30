// This file is loaded by base.html for shared utilities.
// Dashboard-specific JS is inline in dashboard.html.

// Global fetch wrapper with error handling
async function apiFetch(url, options = {}) {
    try {
        const res = await fetch(url, {
            headers: { 'Content-Type': 'application/json', ...options.headers },
            ...options
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({ message: 'Server error' }));
            throw new Error(err.message || `HTTP ${res.status}`);
        }
        return res.json();
    } catch (err) {
        console.error('API Error:', err);
        throw err;
    }
}