// API Helper Functions
const API_BASE = '/api/v1';

async function fetchAPI(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  
  if (!options.headers) {
    options.headers = {};
  }
  
  // Include CSRF token if present (or fetch if missing for write methods)
  let csrfToken = localStorage.getItem("nb_csrf_token");
  if (!csrfToken && options.method && options.method !== 'GET' && endpoint !== '/auth/login') {
    try {
      const meRes = await fetch(`${API_BASE}/auth/me`, { credentials: 'include' });
      if (meRes.ok) {
        const meData = await meRes.json();
        if (meData.data?.csrf_token) {
          csrfToken = meData.data.csrf_token;
          localStorage.setItem("nb_csrf_token", csrfToken);
        }
      }
    } catch (_) {}
  }
  if (csrfToken) {
    options.headers['X-CSRF-Token'] = csrfToken;
  }
  
  if (options.body && !(options.body instanceof FormData)) {
    options.headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(options.body);
  }
  
  options.credentials = 'include';
  
  const response = await fetch(url, options);
  
  // Check if unauthenticated
  if (response.status === 401) {
    if (endpoint !== '/auth/login' && endpoint !== '/auth/me') {
      window.location.reload(); // Will trigger auth flow
    }
    throw new Error('Unauthorized');
  }
  
  if (response.status === 204) {
    return null;
  }
  
  let data = null;
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    try {
      data = await response.json();
    } catch (_) {
      data = null;
    }
  } else {
    await response.text().catch(() => "");
    if (!response.ok) {
      if (response.status === 502 || response.status === 503 || response.status === 504) {
        throw new Error("Backend service is initializing. Please try again shortly.");
      }
      throw new Error(`Request failed (${response.status}): ${response.statusText || 'Server error'}`);
    }
  }
  
  if (!response.ok) {
    throw new Error(data?.error?.message || data?.message || `Request failed (${response.status})`);
  }
  
  return data ? data.data : null;
}

window.api = {
  auth: {
    login: (username, password, remember_me = false) => fetchAPI('/auth/login', {
      method: 'POST',
      body: { username, password, remember_me }
    }),
    logout: () => fetchAPI('/auth/logout', { method: 'POST' }),
    me: () => fetchAPI('/auth/me'),
    changePassword: (current_password, new_password, confirm_password) => fetchAPI('/auth/change-password', {
      method: 'POST',
      body: { current_password, new_password, confirm_password }
    }),
    forgotPassword: (email) => fetchAPI('/auth/forgot-password', {
      method: 'POST',
      body: { email }
    }),
    resetPassword: (token, new_password, confirm_password) => fetchAPI('/auth/reset-password', {
      method: 'POST',
      body: { token, new_password, confirm_password }
    })
  },
  dashboard: {
    summary: () => fetchAPI('/dashboard/summary')
  },
  devices: {
    list: (params = {}) => {
      const qs = new URLSearchParams(params).toString();
      return fetchAPI(`/devices${qs ? '?' + qs : ''}`);
    },
    syncZabbix: () => fetchAPI('/devices/sync-zabbix', { method: 'POST' }),
    backupNow: (deviceId) => fetchAPI(`/devices/${deviceId}/backup`, { method: 'POST' })
  },
  backups: {
    listForDevice: (deviceId, params = {}) => {
      const qs = new URLSearchParams(params).toString();
      return fetchAPI(`/devices/${deviceId}/backup-jobs${qs ? '?' + qs : ''}`);
    }
  },
  settings: {
    get: (deviceId) => fetchAPI(`/devices/${deviceId}/backup-settings`),
    update: (deviceId, driver_key, schedule_enabled, daily_time, retention_policy) => fetchAPI(`/devices/${deviceId}/backup-settings`, {
      method: 'PUT',
      body: { driver_key, schedule_enabled, daily_time, retention_policy }
    })
  },
  storage: {
    test: (data) => fetchAPI('/storage/test', { method: 'POST', body: data }),
    listRepositories: () => fetchAPI('/storage/repositories'),
    getActive: () => fetchAPI('/storage/active'),
    initRepo: (data) => fetchAPI('/storage/repositories/init', { method: 'POST', body: data }),
    unlockRepo: (data) => fetchAPI('/storage/repositories/unlock', { method: 'POST', body: data }),
    activateRepo: (id) => fetchAPI(`/storage/repositories/${id}/activate`, { method: 'POST' }),
    removeRepo: (id) => fetchAPI(`/storage/repositories/${id}`, { method: 'DELETE' }),
    disconnect: () => fetchAPI('/storage/disconnect', { method: 'POST' })
  },
  drivers: {
    list: () => fetchAPI('/drivers'),
    createCustom: (data) => fetchAPI('/drivers/custom', { method: 'POST', body: data }),
    updateCustom: (id, data) => fetchAPI(`/drivers/custom/${id}`, { method: 'PUT', body: data }),
    deleteCustom: (id) => fetchAPI(`/drivers/custom/${id}`, { method: 'DELETE' }),
    test: (data) => fetchAPI('/drivers/test', { method: 'POST', body: data })
  },
  health: {
    ceph: () => fetchAPI('/health/ceph')
  },
  users: {
    list: () => fetchAPI('/users'),
    create: (username, password, role, email = null) => fetchAPI('/users', {
      method: 'POST',
      body: { username, password, role, email }
    }),
    delete: (userId) => fetchAPI(`/users/${userId}`, { method: 'DELETE' })
  },
  snapshots: {
    listForDevice: (deviceId, params = {}) => {
      const qs = new URLSearchParams(params).toString();
      return fetchAPI(`/devices/${deviceId}/snapshots${qs ? '?' + qs : ''}`);
    },
    get: (snapshotId) => fetchAPI(`/snapshots/${snapshotId}`),
    downloadUrl: (snapshotId) => `${API_BASE}/snapshots/${snapshotId}/download`
  },
  reports: {
    download: async (params = {}) => {
      const qs = new URLSearchParams(params).toString();
      const url = `${API_BASE}/reports/export?${qs}`;
      const res = await fetch(url, { credentials: 'include' });
      if (!res.ok) {
        let errMessage = 'Failed to generate report';
        try {
          const errData = await res.json();
          errMessage = errData.error?.message || errData.message || errMessage;
        } catch (_) {}
        throw new Error(errMessage);
      }
      
      const blob = await res.blob();
      const disposition = res.headers.get('Content-Disposition') || '';
      let ext = params.format === 'pdf' ? 'pdf' : 'xlsx';
      let filename = `network_backup_report.${ext}`;
      const match = disposition.match(/filename="?([^"]+)"?/);
      if (match && match[1]) {
        filename = match[1];
      }
      
      const downloadUrl = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(downloadUrl), 1000);
      return filename;
    }
  },
  logs: {
    list: (params = {}) => {
      const qs = new URLSearchParams(params).toString();
      return fetchAPI(`/logs${qs ? '?' + qs : ''}`);
    },
    stats: (params = {}) => {
      const qs = new URLSearchParams(params).toString();
      return fetchAPI(`/logs/stats${qs ? '?' + qs : ''}`);
    },
    get: (logId) => fetchAPI(`/logs/${logId}`),
    download: async (params = {}) => {
      const qs = new URLSearchParams(params).toString();
      const url = `${API_BASE}/logs/export?${qs}`;
      const res = await fetch(url, { credentials: 'include' });
      if (!res.ok) {
        let errMessage = 'Failed to export audit logs';
        try {
          const errData = await res.json();
          errMessage = errData.error?.message || errData.message || errMessage;
        } catch (_) {}
        throw new Error(errMessage);
      }
      
      const blob = await res.blob();
      const disposition = res.headers.get('Content-Disposition') || '';
      let ext = params.format === 'pdf' ? 'pdf' : 'xlsx';
      let filename = `NetBackup_Audit_Log.${ext}`;
      const match = disposition.match(/filename="?([^"]+)"?/);
      if (match && match[1]) {
        filename = match[1];
      }
      
      const downloadUrl = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(downloadUrl), 1000);
      return filename;
    }
  }
};

window.apiFetch = fetchAPI;
window.fetchAPI = fetchAPI;

