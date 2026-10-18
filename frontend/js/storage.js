// S3 Storage Management Dialog Logic
// Restricted strictly to accounts with role 'admin'

let currentTestedParams = null;

function showS3Alert(message, isSuccess = true) {
  const alertEl = document.getElementById("s3-alert");
  if (!alertEl) return;
  alertEl.textContent = message;
  alertEl.classList.remove("hidden");
  if (isSuccess) {
    alertEl.className = "rounded-xl p-3 text-xs font-semibold border border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400";
  } else {
    alertEl.className = "rounded-xl p-3 text-xs font-semibold border border-red-500/30 bg-red-500/10 text-red-600 dark:text-red-400";
  }
}

function hideS3Alert() {
  const alertEl = document.getElementById("s3-alert");
  if (alertEl) alertEl.classList.add("hidden");
}

function openS3TestPopup({ success, title, message, details = {} }) {
  const modal = document.getElementById("s3-test-modal");
  if (!modal) return;

  const iconContainer = document.getElementById("s3-test-modal-icon-container");
  const titleEl = document.getElementById("s3-test-modal-title");
  const subEl = document.getElementById("s3-test-modal-subtitle");
  const bodyEl = document.getElementById("s3-test-modal-body");
  const actionsEl = document.getElementById("s3-test-modal-actions");

  titleEl.textContent = title;
  subEl.textContent = success ? "S3 endpoint and bucket verification passed" : "S3 endpoint connection verification failed";

  if (success) {
    iconContainer.className = "w-10 h-10 rounded-xl flex items-center justify-center shrink-0 border border-emerald-500/30 bg-emerald-500/10 text-emerald-500";
    iconContainer.innerHTML = `
      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
      </svg>
    `;
    const tlsLabel = details.fingerprint
      ? `Auto-Pinned &amp; Secure (${escapeHtml(details.fingerprint.substring(0, 14))}...)`
      : "Verified &amp; Secure";

    bodyEl.className = "p-3.5 rounded-xl border border-emerald-500/20 bg-emerald-500/5 text-xs space-y-2";
    bodyEl.innerHTML = `
      <div class="font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5">
        <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
        <span>${escapeHtml(message)}</span>
      </div>
      <div class="grid grid-cols-2 gap-2 pt-1 border-t border-emerald-500/10 text-[11px]">
        <div><span class="muted">Endpoint:</span> <span class="font-mono block truncate text-slate-800 dark:text-slate-200">${escapeHtml(details.endpoint || "-")}</span></div>
        <div><span class="muted">Bucket:</span> <span class="font-mono block truncate text-slate-800 dark:text-slate-200">${escapeHtml(details.bucket || "-")}</span></div>
        <div><span class="muted">TLS / SSL:</span> <span class="font-semibold text-emerald-600 dark:text-emerald-400">${tlsLabel}</span></div>
        <div><span class="muted">Repository State:</span> <span class="font-semibold text-sky-600 dark:text-sky-400">${details.manifest_exists ? "Manifest Found" : "Clean / Uninitialized"}</span></div>
      </div>
    `;

    actionsEl.innerHTML = `
      <button id="s3-popup-dismiss-btn" type="button"
        class="soft border line hover:border-slate-400 rounded-xl px-4 py-2 font-semibold text-xs transition-colors">
        Close
      </button>
      <button id="s3-popup-continue-btn" type="button"
        class="btn-primary rounded-xl px-4 py-2 font-bold text-xs flex items-center gap-1.5 shadow-md">
        <span>Continue to Next Step</span>
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
        </svg>
      </button>
    `;

    document.getElementById("s3-popup-dismiss-btn").onclick = closeS3TestPopup;
    document.getElementById("s3-popup-continue-btn").onclick = () => {
      closeS3TestPopup();
      handleNextStep();
    };
  } else {
    iconContainer.className = "w-10 h-10 rounded-xl flex items-center justify-center shrink-0 border border-red-500/30 bg-red-500/10 text-red-500";
    iconContainer.innerHTML = `
      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
      </svg>
    `;
    bodyEl.className = "p-3.5 rounded-xl border border-red-500/20 bg-red-500/5 text-xs space-y-1.5";
    bodyEl.innerHTML = `
      <div class="font-semibold text-red-600 dark:text-red-400">
        ${escapeHtml(message)}
      </div>
      <p class="text-[11px] muted">
        Please check your endpoint address, credentials, bucket name, or SSL certificate configuration and try again.
      </p>
    `;

    actionsEl.innerHTML = `
      <button id="s3-popup-dismiss-btn" type="button"
        class="soft border line hover:border-slate-400 rounded-xl px-5 py-2 font-semibold text-xs transition-colors">
        Dismiss
      </button>
    `;
    document.getElementById("s3-popup-dismiss-btn").onclick = closeS3TestPopup;
  }

  modal.classList.remove("hidden");
}

function closeS3TestPopup() {
  const modal = document.getElementById("s3-test-modal");
  if (modal) modal.classList.add("hidden");
}

async function loadActiveRepository() {
  try {
    const res = await window.api.storage.getActive();
    const disconnectBtn = document.getElementById("s3-disconnect-btn");
    const badgeEl = document.getElementById("s3-active-badge");

    // Unwrap repository from dictionary or direct payload
    const repo = (res && res.repository) ? res.repository : res;

    if (repo && repo.id && repo.is_active) {
      document.getElementById("s3-active-name").textContent = repo.name || "-";
      document.getElementById("s3-active-bucket").textContent = repo.bucket || "-";
      document.getElementById("s3-active-endpoint").textContent = repo.endpoint || "-";
      const snapCount = repo.snapshot_count ?? repo.snapshots_count ?? 0;
      document.getElementById("s3-active-snapshots-count").textContent = `${snapCount} snapshot(s)`;
      if (badgeEl) {
        badgeEl.textContent = "ACTIVE";
        badgeEl.className = "font-mono text-[10px] font-bold px-2 py-0.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400";
      }
      if (disconnectBtn) disconnectBtn.classList.remove("hidden");
    } else {
      document.getElementById("s3-active-name").textContent = "Not Connected";
      document.getElementById("s3-active-bucket").textContent = "-";
      document.getElementById("s3-active-endpoint").textContent = "-";
      document.getElementById("s3-active-snapshots-count").textContent = "0 snapshot(s)";
      if (badgeEl) {
        badgeEl.textContent = "NOT CONNECTED";
        badgeEl.className = "font-mono text-[10px] font-bold px-2 py-0.5 rounded-full border border-slate-500/30 bg-slate-500/10 text-slate-600 dark:text-slate-400";
      }
      if (disconnectBtn) disconnectBtn.classList.add("hidden");
    }
  } catch (err) {
    console.error("Failed to load active repository:", err);
  }
}

async function loadRepositoriesTable() {
  const tbody = document.getElementById("s3-repos-tbody");
  if (!tbody) return;

  try {
    const res = await window.api.storage.listRepositories();
    const repos = Array.isArray(res) ? res : (res?.repositories || res?.items || []);
    if (!repos || repos.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" class="py-3 text-center muted">No repositories configured.</td></tr>`;
      return;
    }

    tbody.innerHTML = repos.map(repo => {
      const activeBadge = repo.is_active
        ? `<span class="font-mono text-[10px] font-bold px-2 py-0.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">ACTIVE</span>`
        : `<button type="button" class="s3-activate-btn soft border line hover:border-sky-500 rounded-lg px-2.5 py-1 text-[11px] font-bold text-sky-600 dark:text-sky-400 transition-colors" data-id="${repo.id}">Activate</button>`;

      const removeBtn = `
        <button type="button" class="s3-remove-btn soft border line hover:border-red-500 text-slate-400 hover:text-red-500 hover:bg-red-500/10 rounded-lg p-1 transition-colors" data-id="${repo.id}" data-name="${escapeHtml(repo.name)}" title="Hapus koneksi S3 repository">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
        </button>
      `;

      const snapCount = repo.snapshot_count ?? repo.snapshots_count ?? 0;

      return `
        <tr class="hover:bg-slate-500/5">
          <td class="py-2.5 pr-3 font-semibold text-slate-800 dark:text-slate-200">${escapeHtml(repo.name)}</td>
          <td class="py-2.5 pr-3 font-mono text-slate-600 dark:text-slate-400">${escapeHtml(repo.bucket)}</td>
          <td class="py-2.5 pr-3 font-mono text-slate-500 dark:text-slate-400 text-[11px]">${escapeHtml(repo.endpoint)}</td>
          <td class="py-2.5 pr-3 text-center font-bold text-sky-600 dark:text-sky-400">${snapCount}</td>
          <td class="py-2.5 text-right">
            <div class="flex items-center justify-end gap-1.5">
              ${activeBadge}
              ${removeBtn}
            </div>
          </td>
        </tr>
      `;
    }).join("");

    tbody.querySelectorAll(".s3-activate-btn").forEach(btn => {
      btn.addEventListener("click", async () => {
        const repoId = btn.getAttribute("data-id");
        btn.disabled = true;
        btn.textContent = "Switching...";
        try {
          await window.api.storage.activateRepo(repoId);
          showS3Alert("Repository activated successfully. Scoped snapshots and archives updated.", true);
          await loadActiveRepository();
          await loadRepositoriesTable();
          if (window.devicesModule && window.devicesModule.loadDevices) {
            window.devicesModule.loadDevices();
          }
        } catch (err) {
          showS3Alert(err.message || "Failed to switch repository.", false);
        } finally {
          btn.disabled = false;
        }
      });
    });

    tbody.querySelectorAll(".s3-remove-btn").forEach(btn => {
      btn.addEventListener("click", async () => {
        const repoId = btn.getAttribute("data-id");
        const repoName = btn.getAttribute("data-name");
        if (!confirm(`Hapus koneksi repository "${repoName}"? Data backup di server S3 fisik tidak akan terhapus, namun konfigurasi koneksi di sistem akan dihapus.`)) {
          return;
        }
        btn.disabled = true;
        try {
          await window.api.storage.removeRepo(repoId);
          showS3Alert(`Repository "${repoName}" berhasil dihapus.`, true);
          await loadActiveRepository();
          await loadRepositoriesTable();
          if (window.devicesModule && window.devicesModule.loadDevices) {
            window.devicesModule.loadDevices();
          }
        } catch (err) {
          showS3Alert(err.message || "Failed to remove repository.", false);
        } finally {
          btn.disabled = false;
        }
      });
    });
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="5" class="py-3 text-center text-red-500">Failed to load repositories: ${escapeHtml(err.message || "")}</td></tr>`;
  }
}

async function openS3Dialog() {
  const currentUser = window.authModule?.currentUser();
  if (!currentUser || currentUser.role !== "admin") {
    alert("Access denied: Only Administrator accounts can manage S3 storage repositories.");
    return;
  }

  hideS3Alert();
  resetS3Form();
  await loadActiveRepository();
  await loadRepositoriesTable();

  const dialog = document.getElementById("s3-management-dialog");
  window.openDialog(dialog, document.getElementById("s3-input-name"));
}

function closeS3Dialog() {
  const dialog = document.getElementById("s3-management-dialog");
  window.closeDialog(dialog);
}

function setStep1Locked(locked) {
  document.getElementById("s3-input-name").disabled = locked;
  document.getElementById("s3-input-bucket").disabled = locked;
  document.getElementById("s3-input-endpoint").disabled = locked;
  document.getElementById("s3-input-access-key").disabled = locked;
  document.getElementById("s3-input-secret-key").disabled = locked;
  document.getElementById("s3-input-secure").disabled = locked;
  document.getElementById("s3-test-btn").disabled = locked;
  const nextBtn = document.getElementById("s3-next-btn");
  if (nextBtn) nextBtn.disabled = locked;
}

function resetS3Form() {
  closeS3TestPopup();
  setStep1Locked(false);
  document.getElementById("s3-input-name").value = "";
  document.getElementById("s3-input-bucket").value = "";
  document.getElementById("s3-input-endpoint").value = "";
  document.getElementById("s3-input-access-key").value = "";
  document.getElementById("s3-input-secret-key").value = "";
  document.getElementById("s3-input-secure").checked = true;

  const nextBtn = document.getElementById("s3-next-btn");
  if (nextBtn) nextBtn.disabled = true;

  document.getElementById("s3-step2-container").classList.add("hidden");
  document.getElementById("s3-init-case").classList.add("hidden");
  document.getElementById("s3-unlock-case").classList.add("hidden");
  document.getElementById("s3-master-pass").value = "";
  document.getElementById("s3-confirm-pass").value = "";
  document.getElementById("s3-unlock-pass").value = "";
  currentTestedParams = null;
}

async function handleTestConnection() {
  hideS3Alert();
  closeS3TestPopup();
  const name = document.getElementById("s3-input-name").value.trim();
  const bucket = document.getElementById("s3-input-bucket").value.trim();
  const endpoint = document.getElementById("s3-input-endpoint").value.trim();
  const accessKey = document.getElementById("s3-input-access-key").value.trim();
  const secretKey = document.getElementById("s3-input-secret-key").value.trim();
  const secure = document.getElementById("s3-input-secure").checked;
  const nextBtn = document.getElementById("s3-next-btn");

  if (!name || !bucket || !endpoint || !accessKey || !secretKey) {
    if (nextBtn) nextBtn.disabled = true;
    openS3TestPopup({
      success: false,
      title: "Missing Information",
      message: "Please fill in all repository connection fields (Repository Name, Bucket, Endpoint, Access Key, and Secret Key)."
    });
    return;
  }

  // Strict check: HTTPS endpoints MUST have SSL certificate verification enabled
  if (endpoint.toLowerCase().startsWith("https://") && !secure) {
    if (nextBtn) nextBtn.disabled = true;
    document.getElementById("s3-step2-container").classList.add("hidden");
    openS3TestPopup({
      success: false,
      title: "SSL Validation Required",
      message: "SSL Certificate Validation is required for HTTPS endpoints. Please enable 'Verify SSL / TLS Certificate'."
    });
    return;
  }

  const testBtn = document.getElementById("s3-test-btn");
  const spinner = document.getElementById("s3-test-spinner");
  testBtn.disabled = true;
  if (nextBtn) nextBtn.disabled = true;
  spinner.classList.remove("hidden");

  try {
    const res = await window.api.storage.test({
      name,
      endpoint,
      bucket,
      access_key: accessKey,
      secret_key: secretKey,
      secure
    });

    if (!res || res.success === false) {
      document.getElementById("s3-step2-container").classList.add("hidden");
      if (nextBtn) nextBtn.disabled = true;
      currentTestedParams = null;
      openS3TestPopup({
        success: false,
        title: "Connection Test Failed",
        message: res?.message || "Failed to reach S3 endpoint or bucket."
      });
      return;
    }

    const hasManifest = !!(res.manifest_exists ?? res.has_manifest);
    currentTestedParams = {
      name,
      endpoint,
      bucket,
      access_key: accessKey,
      secret_key: secretKey,
      secure,
      manifest_exists: hasManifest
    };

    // Keep step 2 hidden until user clicks "Next" or continues from popup
    document.getElementById("s3-step2-container").classList.add("hidden");
    if (nextBtn) nextBtn.disabled = false;

    const bucketNotice = hasManifest
      ? "Existing encrypted repository manifest detected."
      : "Empty / uninitialized bucket detected.";

    openS3TestPopup({
      success: true,
      title: "Connection Verified Successfully",
      message: res.message || bucketNotice,
      details: {
        endpoint,
        bucket,
        manifest_exists: !!res.manifest_exists,
        fingerprint: res.pinned_certificate?.fingerprint
      }
    });
  } catch (err) {
    document.getElementById("s3-step2-container").classList.add("hidden");
    if (nextBtn) nextBtn.disabled = true;
    currentTestedParams = null;
    openS3TestPopup({
      success: false,
      title: "Connection Test Failed",
      message: err.message || "Failed to reach S3 endpoint or bucket."
    });
  } finally {
    testBtn.disabled = false;
    spinner.classList.add("hidden");
  }
}

function handleNextStep() {
  hideS3Alert();
  if (!currentTestedParams) {
    showS3Alert("Please test the connection first before proceeding.", false);
    return;
  }

  // Lock Step 1 fields and controls so credentials and verification checkbox cannot be edited
  setStep1Locked(true);

  // Display Step 2 (Entry Master Password)
  const step2 = document.getElementById("s3-step2-container");
  const statusMsg = document.getElementById("s3-step2-status");
  const initCase = document.getElementById("s3-init-case");
  const unlockCase = document.getElementById("s3-unlock-case");

  step2.classList.remove("hidden");

  if (currentTestedParams.manifest_exists) {
    statusMsg.innerHTML = `<span class="w-2 h-2 rounded-full bg-emerald-500"></span> <span>Connection Verified: Encrypted Repository Manifest Found</span>`;
    unlockCase.classList.remove("hidden");
    initCase.classList.add("hidden");
    document.getElementById("s3-unlock-pass").focus();
  } else {
    statusMsg.innerHTML = `<span class="w-2 h-2 rounded-full bg-sky-500"></span> <span>Connection Verified: Empty / Uninitialized Bucket Detected</span>`;
    initCase.classList.remove("hidden");
    unlockCase.classList.add("hidden");
    document.getElementById("s3-master-pass").focus();
  }
}

async function handleInitRepository() {
  hideS3Alert();
  if (!currentTestedParams) {
    showS3Alert("Please test the connection first.", false);
    return;
  }

  const pass = document.getElementById("s3-master-pass").value;
  const confirm = document.getElementById("s3-confirm-pass").value;

  if (!pass || pass.length < 8) {
    showS3Alert("Master password must be at least 8 characters long.", false);
    return;
  }
  if (pass !== confirm) {
    showS3Alert("Master password confirmation does not match.", false);
    return;
  }

  const btn = document.getElementById("s3-init-btn");
  btn.disabled = true;
  btn.textContent = "Initializing...";

  try {
    await window.api.storage.initRepo({
      ...currentTestedParams,
      master_password: pass
    });

    showS3Alert("Repository initialized and mounted successfully.", true);
    resetS3Form();
    await loadActiveRepository();
    await loadRepositoriesTable();
    if (window.devicesModule && window.devicesModule.loadDevices) {
      window.devicesModule.loadDevices();
    }
  } catch (err) {
    showS3Alert(err.message || "Failed to initialize repository.", false);
  } finally {
    btn.disabled = false;
    btn.textContent = "Initialize & Mount Repository";
  }
}

async function handleUnlockRepository() {
  hideS3Alert();
  if (!currentTestedParams) {
    showS3Alert("Please test the connection first.", false);
    return;
  }

  const pass = document.getElementById("s3-unlock-pass").value;
  if (!pass) {
    showS3Alert("Please enter the Master Password to unlock the repository.", false);
    return;
  }

  const btn = document.getElementById("s3-unlock-btn");
  btn.disabled = true;
  btn.textContent = "Unlocking...";

  try {
    await window.api.storage.unlockRepo({
      ...currentTestedParams,
      master_password: pass
    });

    showS3Alert("Repository unlocked and mounted successfully.", true);
    resetS3Form();
    await loadActiveRepository();
    await loadRepositoriesTable();
    if (window.devicesModule && window.devicesModule.loadDevices) {
      window.devicesModule.loadDevices();
    }
  } catch (err) {
    showS3Alert(err.message || "Failed to unlock repository. Invalid master password.", false);
  } finally {
    btn.disabled = false;
    btn.textContent = "Unlock & Mount Repository";
  }
}

async function handleDisconnectRepository() {
  hideS3Alert();
  if (!confirm("Are you sure you want to disconnect the currently active S3 storage repository?")) {
    return;
  }

  const disconnectBtn = document.getElementById("s3-disconnect-btn");
  if (disconnectBtn) {
    disconnectBtn.disabled = true;
    disconnectBtn.textContent = "Disconnecting...";
  }

  try {
    await window.api.storage.disconnect();
    showS3Alert("S3 repository disconnected successfully.", true);
    await loadActiveRepository();
    await loadRepositoriesTable();
    if (window.devicesModule && window.devicesModule.loadDevices) {
      window.devicesModule.loadDevices();
    }
  } catch (err) {
    showS3Alert(err.message || "Failed to disconnect repository.", false);
  } finally {
    if (disconnectBtn) {
      disconnectBtn.disabled = false;
      disconnectBtn.textContent = "Disconnect Repository";
    }
  }
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

document.addEventListener("DOMContentLoaded", () => {
  const triggerBtn = document.getElementById("s3-management-btn");
  if (triggerBtn) {
    triggerBtn.addEventListener("click", () => {
      const menu = document.getElementById("admin-menu");
      if (menu) menu.hidden = true;
      openS3Dialog();
    });
  }

  const closeX = document.getElementById("s3-close-x");
  if (closeX) closeX.addEventListener("click", closeS3Dialog);

  const cancelBtn = document.getElementById("s3-cancel-btn");
  if (cancelBtn) cancelBtn.addEventListener("click", closeS3Dialog);

  const resetBtn = document.getElementById("s3-reset-btn");
  if (resetBtn) {
    resetBtn.addEventListener("click", () => {
      resetS3Form();
      hideS3Alert();
    });
  }

  const disconnectBtn = document.getElementById("s3-disconnect-btn");
  if (disconnectBtn) disconnectBtn.addEventListener("click", handleDisconnectRepository);

  const testBtn = document.getElementById("s3-test-btn");
  if (testBtn) testBtn.addEventListener("click", handleTestConnection);

  const testModalCloseX = document.getElementById("s3-test-modal-close-x");
  if (testModalCloseX) testModalCloseX.addEventListener("click", closeS3TestPopup);

  const nextBtn = document.getElementById("s3-next-btn");
  if (nextBtn) nextBtn.addEventListener("click", handleNextStep);

  const initBtn = document.getElementById("s3-init-btn");
  if (initBtn) initBtn.addEventListener("click", handleInitRepository);

  const unlockBtn = document.getElementById("s3-unlock-btn");
  if (unlockBtn) unlockBtn.addEventListener("click", handleUnlockRepository);
});

window.storageModule = {
  openS3Dialog,
  closeS3Dialog,
  loadActiveRepository,
  loadRepositoriesTable
};
