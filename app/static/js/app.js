/**
 * Hermes Librarian — Frontend Interactivity
 */

// 1. Theme Management (Dark / Light)
function initTheme() {
  const storedTheme = localStorage.getItem('hlib_theme');
  const isDark = storedTheme === 'dark' ||
    (!storedTheme && window.matchMedia('(prefers-color-scheme: dark)').matches);
  if (isDark) {
    document.documentElement.classList.add('dark');
  } else {
    document.documentElement.classList.remove('dark');
  }
}

function toggleTheme() {
  const html = document.documentElement;
  const isDark = html.classList.toggle('dark');
  localStorage.setItem('hlib_theme', isDark ? 'dark' : 'light');
}

// Auth headers helper
function getAuthHeaders(extraHeaders = {}) {
  const headers = { 'Content-Type': 'application/json', ...extraHeaders };
  const token = localStorage.getItem('hlib_api_key');
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
    headers['X-API-Key'] = token;
  }
  return headers;
}

// 2. Quick Add Modal
function openAddModal() {
  const modal = document.getElementById('add-link-modal');
  if (modal) {
    modal.classList.remove('hidden');
    modal.classList.add('flex');
    const input = document.getElementById('add-url-input');
    if (input) {
      input.value = '';
      setTimeout(() => input.focus(), 50);
    }
  }
}

function closeAddModal() {
  const modal = document.getElementById('add-link-modal');
  if (modal) {
    modal.classList.add('hidden');
    modal.classList.remove('flex');
    const errorEl = document.getElementById('add-modal-error');
    if (errorEl) errorEl.classList.add('hidden');
    const btn = document.getElementById('add-submit-btn');
    if (btn) btn.disabled = false;
  }
}

async function handleAddLink(event) {
  event.preventDefault();
  const urlInput = document.getElementById('add-url-input');
  const tagsInput = document.getElementById('add-tags-input');
  const statusSelect = document.getElementById('add-status-select');
  const errorEl = document.getElementById('add-modal-error');
  const submitBtn = document.getElementById('add-submit-btn');
  const spinner = document.getElementById('add-spinner');

  const url = urlInput.value.trim();
  if (!url) return;

  const rawTags = tagsInput ? tagsInput.value.trim() : '';
  const tags = rawTags ? rawTags.split(/[,\s]+/).map(t => t.replace(/^#/, '').toLowerCase()).filter(Boolean) : null;
  const status = statusSelect ? statusSelect.value : 'inbox';

  try {
    submitBtn.disabled = true;
    if (spinner) spinner.classList.remove('hidden');
    if (errorEl) errorEl.classList.add('hidden');

    const res = await fetch('/api/links', {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ url, tags, status }),
    });

    if (!res.ok) {
      const data = await res.json();
      throw new Error(data.detail || 'Failed to archive link');
    }

    closeAddModal();
    window.location.reload();
  } catch (err) {
    if (errorEl) {
      errorEl.textContent = err.message;
      errorEl.classList.remove('hidden');
    }
  } finally {
    submitBtn.disabled = false;
    if (spinner) spinner.classList.add('hidden');
  }
}

// 3. Status Change Handler
async function updateLinkStatus(linkId, newStatus) {
  try {
    const res = await fetch(`/api/links/${linkId}`, {
      method: 'PATCH',
      headers: getAuthHeaders(),
      body: JSON.stringify({ status: newStatus }),
    });
    if (!res.ok) throw new Error('Status update failed');
  } catch (err) {
    console.error(err);
    alert('Failed to update status: ' + err.message);
  }
}

// 4. Delete Link Handler
async function deleteLink(linkId, title) {
  if (!confirm(`Are you sure you want to delete "${title}"?`)) return;

  try {
    const res = await fetch(`/api/links/${linkId}`, { 
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error('Delete failed');

    const card = document.getElementById(`link-item-${linkId}`);
    if (card) {
      card.style.transition = 'opacity 0.3s, transform 0.3s';
      card.style.opacity = '0';
      card.style.transform = 'scale(0.95)';
      setTimeout(() => card.remove(), 300);
    } else {
      window.location.reload();
    }
  } catch (err) {
    alert('Error deleting link: ' + err.message);
  }
}

// 5. Vault Sync
async function syncVault() {
  const btn = document.getElementById('sync-vault-btn');
  if (btn) btn.disabled = true;
  try {
    const res = await fetch('/api/sync', { 
      method: 'POST',
      headers: getAuthHeaders(),
    });
    const data = await res.json();
    alert(`Vault sync complete! Synced ${data.synced_files} files.`);
    window.location.reload();
  } catch (err) {
    alert('Failed to sync vault: ' + err.message);
  } finally {
    if (btn) btn.disabled = false;
  }
}

// 6. Global Keyboard Shortcuts
document.addEventListener('keydown', (e) => {
  // Ignore if inside an input or textarea
  if (['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName)) {
    if (e.key === 'Escape') closeAddModal();
    return;
  }

  // 'c' or 'a' opens Quick Add
  if (e.key === 'c' || e.key === 'a') {
    e.preventDefault();
    openAddModal();
  }

  // '/' focuses search
  if (e.key === '/') {
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
      e.preventDefault();
      searchInput.focus();
    }
  }
});

// 7. Bookmarklet Modal
function openBookmarkletModal() {
  const modal = document.getElementById('bookmarklet-modal');
  if (modal) {
    modal.classList.remove('hidden');
    modal.classList.add('flex');
  }
}

function closeBookmarkletModal() {
  const modal = document.getElementById('bookmarklet-modal');
  if (modal) {
    modal.classList.add('hidden');
    modal.classList.remove('flex');
  }
}

// 8. Import / Export Modal
function openImportExportModal() {
  const modal = document.getElementById('import-export-modal');
  if (modal) {
    modal.classList.remove('hidden');
    modal.classList.add('flex');
  }
}

function closeImportExportModal() {
  const modal = document.getElementById('import-export-modal');
  if (modal) {
    modal.classList.add('hidden');
    modal.classList.remove('flex');
  }
}

async function handleImportBookmarks(event) {
  event.preventDefault();
  const fileInput = document.getElementById('import-file-input');
  const btn = document.getElementById('import-submit-btn');
  const statusEl = document.getElementById('import-status');

  if (!fileInput.files || fileInput.files.length === 0) return;

  const file = fileInput.files[0];
  const formData = new FormData();
  formData.append('file', file);

  try {
    btn.disabled = true;
    btn.textContent = 'Importing...';
    statusEl.classList.remove('hidden');
    statusEl.className = 'mt-2 text-xs text-blue-500';
    statusEl.textContent = 'Processing bookmarks file...';

    const headers = {};
    const token = localStorage.getItem('hlib_api_key');
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
      headers['X-API-Key'] = token;
    }

    const res = await fetch('/api/import/bookmarks', {
      method: 'POST',
      headers: headers,
      body: formData,
    });

    if (!res.ok) throw new Error('Import failed');
    const data = await res.json();

    statusEl.className = 'mt-2 text-xs text-emerald-600 font-semibold';
    statusEl.textContent = `✓ Successfully imported ${data.imported} bookmarks! (${data.errors} skipped)`;

    setTimeout(() => {
      window.location.reload();
    }, 1500);

  } catch (err) {
    statusEl.className = 'mt-2 text-xs text-red-500 font-semibold';
    statusEl.textContent = 'Failed: ' + err.message;
  } finally {
    btn.disabled = false;
    btn.textContent = 'Import';
  }
}

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', () => {
  initTheme();
});
