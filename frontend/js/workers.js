// Backup Worker Management Dialog Logic
// Restricted strictly to accounts with role 'admin'

let cachedDrivers = [];
let cachedDevices = [];

const WORKER_PRESETS = {
  huawei_vrp: {
    key: "huawei_vrp",
    label: "Huawei VRP Switch",
    vendor: "Huawei",
    model: "S5700 Series",
    port: 22,
    conn_timeout: 15,
    cmd_timeout: 30,
    need_enable: false,
    enable_cmd: "enable",
    enable_prompt: "[>#]",
    paging_cmd: "screen-length 0 temporary",
    paging_mode: "disable_command",
    backup_cmd: "display current-configuration",
    output_ext: "cfg",
    strip_patterns: "^! Last configuration.*\n^#\\s*return",
    min_length: 50,
    req_keyword: "sysname"
  },
  cisco_ios: {
    key: "cisco_ios",
    label: "Cisco IOS Switch/Router",
    vendor: "Cisco",
    model: "Catalyst / ISR",
    port: 22,
    conn_timeout: 15,
    cmd_timeout: 30,
    need_enable: true,
    enable_cmd: "enable",
    enable_prompt: "[>#]",
    paging_cmd: "terminal length 0",
    paging_mode: "disable_command",
    backup_cmd: "show running-config",
    output_ext: "cfg",
    strip_patterns: "^! Last configuration change at.*\n^! NVRAM config last updated at.*",
    min_length: 50,
    req_keyword: "version"
  },
  cisco_nxos: {
    key: "cisco_nxos",
    label: "Cisco Nexus (NX-OS)",
    vendor: "Cisco",
    model: "Nexus 9000/7000",
    port: 22,
    conn_timeout: 15,
    cmd_timeout: 30,
    need_enable: false,
    enable_cmd: "enable",
    enable_prompt: "[>#]",
    paging_cmd: "terminal length 0",
    paging_mode: "disable_command",
    backup_cmd: "show running-config",
    output_ext: "cfg",
    strip_patterns: "^!Command: show running-config\n^!Running configuration last done at:.*",
    min_length: 50,
    req_keyword: "version"
  },
  aruba_procurve: {
    key: "aruba_procurve",
    label: "HP / Aruba ProCurve",
    vendor: "Aruba",
    model: "2930F / 2530",
    port: 22,
    conn_timeout: 15,
    cmd_timeout: 30,
    need_enable: false,
    enable_cmd: "enable",
    enable_prompt: "[>#]",
    paging_cmd: "no page",
    paging_mode: "disable_command",
    backup_cmd: "show running-config",
    output_ext: "cfg",
    strip_patterns: "^; .* Configuration Editor",
    min_length: 50,
    req_keyword: "hostname"
  },
  fortinet_fortios: {
    key: "fortinet_fortios",
    label: "FortiGate Firewall (CLI)",
    vendor: "Fortinet",
    model: "FortiGate 60F/100F",
    port: 22,
    conn_timeout: 15,
    cmd_timeout: 30,
    need_enable: false,
    enable_cmd: "enable",
    enable_prompt: "[>#]",
    paging_cmd: "config system console\nset output standard\nend",
    paging_mode: "disable_command",
    backup_cmd: "show full-configuration",
    output_ext: "conf",
    strip_patterns: "^#config-version=.*",
    min_length: 50,
    req_keyword: "config system"
  },
  sangfor_ngaf_cli: {
    key: "sangfor_ngaf_cli",
    label: "Sangfor NGAF Firewall (CLI)",
    vendor: "Sangfor",
    model: "NGAF Series",
    port: 22,
    conn_timeout: 15,
    cmd_timeout: 30,
    need_enable: false,
    enable_cmd: "enable",
    enable_prompt: "[>#]",
    paging_cmd: "",
    paging_mode: "disable_command",
    backup_cmd: "show running-configuration",
    output_ext: "txt",
    strip_patterns: "",
    min_length: 30,
    req_keyword: ""
  }
};

function showWorkerAlert(message, isSuccess = true) {
  const alertEl = document.getElementById("workers-alert");
  if (!alertEl) return;
  alertEl.textContent = message;
  alertEl.classList.remove("hidden");
  if (isSuccess) {
    alertEl.className = "rounded-xl p-3 text-xs font-semibold border border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400";
  } else {
    alertEl.className = "rounded-xl p-3 text-xs font-semibold border border-red-500/30 bg-red-500/10 text-red-600 dark:text-red-400";
  }
}

function hideWorkerAlert() {
  const alertEl = document.getElementById("workers-alert");
  if (alertEl) alertEl.classList.add("hidden");
}

async function loadWorkersTable() {
  const tbody = document.getElementById("workers-table-body");
  if (!tbody) return;

  try {
    const res = await window.api.drivers.list();
    cachedDrivers = (res && res.items) ? res.items : (Array.isArray(res) ? res : []);

    if (cachedDrivers.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" class="py-4 text-center muted">No backup workers registered.</td></tr>`;
      return;
    }

    tbody.innerHTML = cachedDrivers.map(d => {
      const isCustom = d.is_custom === true;
      const typeBadge = isCustom
        ? `<span class="font-mono text-[10px] font-bold px-2 py-0.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">CUSTOM SSH</span>`
        : `<span class="font-mono text-[10px] font-bold px-2 py-0.5 rounded-full border border-sky-500/30 bg-sky-500/10 text-sky-600 dark:text-sky-400">BUILT-IN</span>`;

      const actions = isCustom
        ? `
          <div class="flex items-center justify-end gap-1.5">
            <button type="button" class="worker-edit-btn soft border line hover:border-sky-500 rounded-lg px-2.5 py-1 text-[11px] font-bold text-sky-600 dark:text-sky-400 transition-colors" data-id="${d.id || d.key}">Edit</button>
            <button type="button" class="worker-del-btn soft border line hover:border-red-500 rounded-lg px-2.5 py-1 text-[11px] font-bold text-red-600 dark:text-red-400 transition-colors" data-id="${d.id || d.key}">Delete</button>
          </div>
        `
        : `<span class="muted text-[11px] font-mono">Protected</span>`;

      const vendorModel = [d.vendor_hint, d.model_hint].filter(Boolean).join(" / ") || "Generic";

      return `
        <tr class="hover:bg-slate-500/5">
          <td class="py-2.5 px-3">
            <div class="font-semibold text-slate-800 dark:text-slate-100">${escapeHtml(d.label || d.name || d.key)}</div>
            <div class="font-mono text-[10px] text-slate-500 dark:text-slate-400">${escapeHtml(d.key)}</div>
          </td>
          <td class="py-2.5 px-3 text-slate-600 dark:text-slate-300">${escapeHtml(vendorModel)}</td>
          <td class="py-2.5 px-3">${typeBadge}</td>
          <td class="py-2.5 px-3 font-mono text-[11px] text-slate-600 dark:text-slate-300">.${escapeHtml(d.output_extension || 'txt')}</td>
          <td class="py-2.5 px-3 text-right">${actions}</td>
        </tr>
      `;
    }).join("");

    tbody.querySelectorAll(".worker-edit-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const id = btn.getAttribute("data-id");
        const found = cachedDrivers.find(d => (d.id == id || d.key == id));
        if (found) openWorkerForm(found);
      });
    });

    tbody.querySelectorAll(".worker-del-btn").forEach(btn => {
      btn.addEventListener("click", async () => {
        const id = btn.getAttribute("data-id");
        if (!confirm("Are you sure you want to delete this custom backup worker?")) return;
        try {
          await window.api.drivers.deleteCustom(id);
          showWorkerAlert("Custom worker driver removed successfully.", true);
          await loadWorkersTable();
          if (window.devicesModule && window.devicesModule.loadDevices) {
            window.devicesModule.loadDevices();
          }
        } catch (err) {
          showWorkerAlert(err.message || "Failed to remove worker driver.", false);
        }
      });
    });
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="5" class="py-4 text-center text-red-500">Failed to load backup workers.</td></tr>`;
  }
}

async function populateTestDeviceSelect() {
  const select = document.getElementById("worker-test-device-select");
  if (!select) return;

  try {
    const res = await window.api.devices.list({ limit: 100 });
    cachedDevices = res?.items || [];
    select.innerHTML = `<option value="">-- Select Target Device --</option>` +
      cachedDevices.map(d => `<option value="${d.id}">${escapeHtml(d.hostname)} (${escapeHtml(d.ip_address)}) [${escapeHtml(d.vendor || 'Unknown')}]</option>`).join("");
  } catch (_) {}
}

function applyWorkerTemplate(templateKey) {
  const p = WORKER_PRESETS[templateKey];
  if (!p) return;

  const keyInput = document.getElementById("worker-field-key");
  if (!keyInput.disabled) {
    keyInput.value = p.key;
  }
  document.getElementById("worker-field-label").value = p.label;
  document.getElementById("worker-field-vendor").value = p.vendor;
  document.getElementById("worker-field-model").value = p.model;
  document.getElementById("worker-field-port").value = p.port;
  document.getElementById("worker-field-conn-timeout").value = p.conn_timeout;
  document.getElementById("worker-field-cmd-timeout").value = p.cmd_timeout;

  const needEnableCheckbox = document.getElementById("worker-field-need-enable");
  needEnableCheckbox.checked = p.need_enable;
  document.getElementById("worker-enable-fields").classList.toggle("hidden", !p.need_enable);
  document.getElementById("worker-field-enable-cmd").value = p.enable_cmd;
  document.getElementById("worker-field-enable-prompt").value = p.enable_prompt;

  document.getElementById("worker-field-paging-cmd").value = p.paging_cmd;
  document.getElementById("worker-field-paging-mode").value = p.paging_mode;
  document.getElementById("worker-field-backup-cmd").value = p.backup_cmd;
  document.getElementById("worker-field-output-ext").value = p.output_ext;
  document.getElementById("worker-field-strip-patterns").value = p.strip_patterns;
  document.getElementById("worker-field-min-length").value = p.min_length;
  document.getElementById("worker-field-req-keyword").value = p.req_keyword;

  showWorkerAlert(`Template '${p.label}' applied. You can adjust parameters as needed.`, true);
}

function openWorkerForm(driver = null) {
  hideWorkerAlert();
  document.getElementById("workers-list-section").classList.add("hidden");
  document.getElementById("workers-form-section").classList.remove("hidden");
  document.getElementById("worker-test-preview").classList.add("hidden");
  populateTestDeviceSelect();

  const titleEl = document.getElementById("worker-form-title");
  const keyInput = document.getElementById("worker-field-key");
  const templateSelect = document.getElementById("worker-template-select");
  if (templateSelect) templateSelect.value = "";

  if (driver) {
    titleEl.textContent = `Edit Worker: ${driver.label || driver.key}`;
    document.getElementById("worker-edit-id").value = driver.id || driver.key;
    keyInput.value = driver.key;
    keyInput.disabled = true;
    document.getElementById("worker-field-label").value = driver.label || "";
    document.getElementById("worker-field-vendor").value = driver.vendor_hint || "";
    document.getElementById("worker-field-model").value = driver.model_hint || "";
    document.getElementById("worker-field-port").value = driver.default_port || 22;
    document.getElementById("worker-field-conn-timeout").value = driver.connect_timeout || 15;
    document.getElementById("worker-field-cmd-timeout").value = driver.command_timeout || 30;

    const needEnable = !!driver.need_enable;
    document.getElementById("worker-field-need-enable").checked = needEnable;
    document.getElementById("worker-enable-fields").classList.toggle("hidden", !needEnable);
    document.getElementById("worker-field-enable-cmd").value = driver.enable_command || "enable";
    document.getElementById("worker-field-enable-prompt").value = driver.enable_prompt_pattern || "[>#]";

    document.getElementById("worker-field-paging-cmd").value = driver.disable_paging_command || "";
    document.getElementById("worker-field-paging-mode").value = driver.paging_mode || "disable_command";
    document.getElementById("worker-field-backup-cmd").value = driver.backup_command || "";
    document.getElementById("worker-field-output-ext").value = driver.output_extension || "cfg";

    const stripArr = Array.isArray(driver.strip_patterns) ? driver.strip_patterns : [];
    document.getElementById("worker-field-strip-patterns").value = stripArr.join("\n");
    document.getElementById("worker-field-min-length").value = driver.validation_min_length || 50;
    document.getElementById("worker-field-req-keyword").value = driver.validation_required_keyword || "";
  } else {
    titleEl.textContent = "Add Custom Backup Worker";
    document.getElementById("worker-edit-id").value = "";
    keyInput.value = "";
    keyInput.disabled = false;
    document.getElementById("worker-field-label").value = "";
    document.getElementById("worker-field-vendor").value = "";
    document.getElementById("worker-field-model").value = "";
    document.getElementById("worker-field-port").value = "22";
    document.getElementById("worker-field-conn-timeout").value = "15";
    document.getElementById("worker-field-cmd-timeout").value = "30";

    document.getElementById("worker-field-need-enable").checked = false;
    document.getElementById("worker-enable-fields").classList.add("hidden");
    document.getElementById("worker-field-enable-cmd").value = "enable";
    document.getElementById("worker-field-enable-prompt").value = "[>#]";

    document.getElementById("worker-field-paging-cmd").value = "";
    document.getElementById("worker-field-paging-mode").value = "disable_command";
    document.getElementById("worker-field-backup-cmd").value = "";
    document.getElementById("worker-field-output-ext").value = "cfg";
    document.getElementById("worker-field-strip-patterns").value = "";
    document.getElementById("worker-field-min-length").value = "50";
    document.getElementById("worker-field-req-keyword").value = "";
  }
}

function closeWorkerForm() {
  document.getElementById("workers-form-section").classList.add("hidden");
  document.getElementById("workers-list-section").classList.remove("hidden");
}

async function handleSaveWorker() {
  hideWorkerAlert();
  const id = document.getElementById("worker-edit-id").value;
  const key = document.getElementById("worker-field-key").value.trim().toLowerCase();
  const label = document.getElementById("worker-field-label").value.trim();
  const vendor = document.getElementById("worker-field-vendor").value.trim();
  const model = document.getElementById("worker-field-model").value.trim();
  const port = parseInt(document.getElementById("worker-field-port").value, 10) || 22;
  const connTimeout = parseInt(document.getElementById("worker-field-conn-timeout").value, 10) || 15;
  const cmdTimeout = parseInt(document.getElementById("worker-field-cmd-timeout").value, 10) || 30;

  const needEnable = document.getElementById("worker-field-need-enable").checked;
  const enableCmd = document.getElementById("worker-field-enable-cmd").value.trim();
  const enablePrompt = document.getElementById("worker-field-enable-prompt").value.trim();

  const pagingCmd = document.getElementById("worker-field-paging-cmd").value.trim();
  const pagingMode = document.getElementById("worker-field-paging-mode").value;
  const backupCmd = document.getElementById("worker-field-backup-cmd").value.trim();
  const outputExt = document.getElementById("worker-field-output-ext").value.trim().replace(/^\./, '');

  const stripRaw = document.getElementById("worker-field-strip-patterns").value;
  const stripPatterns = stripRaw.split("\n").map(s => s.trim()).filter(Boolean);

  const minLen = parseInt(document.getElementById("worker-field-min-length").value, 10) || 50;
  const reqKeyword = document.getElementById("worker-field-req-keyword").value.trim();

  if (!key || !label || !backupCmd || !outputExt) {
    showWorkerAlert("Driver Key, Display Label, Backup Command, and Output Extension are required fields.", false);
    return;
  }

  const payload = {
    key,
    label,
    vendor_hint: vendor || null,
    model_hint: model || null,
    transport: "ssh",
    default_port: port,
    connect_timeout: connTimeout,
    command_timeout: cmdTimeout,
    need_enable: needEnable,
    enable_command: enableCmd || null,
    enable_prompt_pattern: enablePrompt || null,
    disable_paging_command: pagingCmd || null,
    paging_mode: pagingMode,
    backup_command: backupCmd,
    output_extension: outputExt,
    strip_patterns: stripPatterns,
    validation_min_length: minLen,
    validation_required_keyword: reqKeyword || null
  };

  const saveBtn = document.getElementById("worker-save-btn");
  saveBtn.disabled = true;
  saveBtn.textContent = "Saving...";

  try {
    if (id) {
      await window.api.drivers.updateCustom(id, payload);
      showWorkerAlert(`Worker '${label}' updated successfully.`, true);
    } else {
      await window.api.drivers.createCustom(payload);
      showWorkerAlert(`Worker '${label}' registered successfully.`, true);
    }
    closeWorkerForm();
    await loadWorkersTable();
    if (window.devicesModule && window.devicesModule.loadDevices) {
      window.devicesModule.loadDevices();
    }
  } catch (err) {
    showWorkerAlert(err.message || "Failed to save worker driver.", false);
  } finally {
    saveBtn.disabled = false;
    saveBtn.textContent = "Save Worker";
  }
}

async function handleTestWorker() {
  const deviceId = document.getElementById("worker-test-device-select").value;
  const password = document.getElementById("worker-test-password").value;
  const enablePassword = document.getElementById("worker-test-enable-password").value;
  const previewBox = document.getElementById("worker-test-preview");

  if (!deviceId) {
    showWorkerAlert("Please select a target device for testing.", false);
    return;
  }
  if (!password) {
    showWorkerAlert("SSH password is required to perform live test extraction.", false);
    return;
  }

  const testBtn = document.getElementById("worker-test-btn");
  const spinner = document.getElementById("worker-test-spinner");
  testBtn.disabled = true;
  spinner.classList.remove("hidden");
  previewBox.classList.add("hidden");

  const stripRaw = document.getElementById("worker-field-strip-patterns").value;
  const stripPatterns = stripRaw.split("\n").map(s => s.trim()).filter(Boolean);

  const driverConfig = {
    key: document.getElementById("worker-field-key").value.trim().toLowerCase(),
    label: document.getElementById("worker-field-label").value.trim(),
    default_port: parseInt(document.getElementById("worker-field-port").value, 10) || 22,
    connect_timeout: parseInt(document.getElementById("worker-field-conn-timeout").value, 10) || 15,
    command_timeout: parseInt(document.getElementById("worker-field-cmd-timeout").value, 10) || 30,
    need_enable: document.getElementById("worker-field-need-enable").checked,
    enable_command: document.getElementById("worker-field-enable-cmd").value.trim() || null,
    enable_prompt_pattern: document.getElementById("worker-field-enable-prompt").value.trim() || null,
    disable_paging_command: document.getElementById("worker-field-paging-cmd").value.trim() || null,
    paging_mode: document.getElementById("worker-field-paging-mode").value,
    backup_command: document.getElementById("worker-field-backup-cmd").value.trim(),
    output_extension: document.getElementById("worker-field-output-ext").value.trim(),
    strip_patterns: stripPatterns,
    validation_min_length: parseInt(document.getElementById("worker-field-min-length").value, 10) || 50,
    validation_required_keyword: document.getElementById("worker-field-req-keyword").value.trim() || null
  };

  try {
    const res = await window.api.drivers.test({
      device_id: parseInt(deviceId, 10),
      driver_data: {
        ...driverConfig,
        password,
        enable_password: enablePassword || null
      }
    });

    if (res && res.success === false) {
      throw new Error(res.message || "Test execution returned failure.");
    }

    previewBox.classList.remove("hidden");
    previewBox.className = "p-2.5 rounded-lg border border-emerald-500/30 bg-emerald-500/5 font-mono text-[11px] max-h-48 overflow-y-auto whitespace-pre-wrap text-emerald-700 dark:text-emerald-300";
    previewBox.textContent = `[SUCCESS] ${res.message || 'Configuration output extracted successfully.'}\nRaw size: ${res.raw_size_bytes || 0} bytes | Normalized: ${res.normalized_size_bytes || 0} bytes\n\n--- CONFIGURATION OUTPUT PREVIEW ---\n${res.preview || "(Empty output)"}`;
    showWorkerAlert("Live test extraction completed and output verified.", true);
  } catch (err) {
    previewBox.classList.remove("hidden");
    previewBox.className = "p-2.5 rounded-lg border border-red-500/30 bg-red-500/5 font-mono text-[11px] max-h-48 overflow-y-auto whitespace-pre-wrap text-red-600 dark:text-red-400";
    previewBox.textContent = `[FAILED] ${err.message || "Execution error occurred"}`;
    showWorkerAlert(err.message || "Driver extraction test failed.", false);
  } finally {
    testBtn.disabled = false;
    spinner.classList.add("hidden");
  }
}

async function openWorkersDialog() {
  const currentUser = window.authModule?.currentUser();
  if (!currentUser || currentUser.role !== "admin") {
    alert("Access denied: Only Administrator accounts can manage backup workers.");
    return;
  }

  hideWorkerAlert();
  closeWorkerForm();
  await loadWorkersTable();

  const dialog = document.getElementById("workers-management-dialog");
  window.openDialog(dialog, document.getElementById("worker-open-create-btn"));
}

function closeWorkersDialog() {
  const dialog = document.getElementById("workers-management-dialog");
  window.closeDialog(dialog);
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
  const triggerBtn = document.getElementById("workers-management-btn");
  if (triggerBtn) {
    triggerBtn.addEventListener("click", () => {
      const menu = document.getElementById("admin-menu");
      if (menu) menu.hidden = true;
      openWorkersDialog();
    });
  }

  const closeX = document.getElementById("workers-close-x");
  if (closeX) closeX.addEventListener("click", closeWorkersDialog);

  const cancelBtn = document.getElementById("workers-cancel-btn");
  if (cancelBtn) cancelBtn.addEventListener("click", closeWorkersDialog);

  const openCreateBtn = document.getElementById("worker-open-create-btn");
  if (openCreateBtn) openCreateBtn.addEventListener("click", () => openWorkerForm(null));

  const backBtn = document.getElementById("worker-back-to-list-btn");
  if (backBtn) backBtn.addEventListener("click", closeWorkerForm);

  const cancelEditBtn = document.getElementById("worker-cancel-edit-btn");
  if (cancelEditBtn) cancelEditBtn.addEventListener("click", closeWorkerForm);

  const saveBtn = document.getElementById("worker-save-btn");
  if (saveBtn) saveBtn.addEventListener("click", handleSaveWorker);

  const testBtn = document.getElementById("worker-test-btn");
  if (testBtn) testBtn.addEventListener("click", handleTestWorker);

  const templateSelect = document.getElementById("worker-template-select");
  if (templateSelect) {
    templateSelect.addEventListener("change", (e) => {
      if (e.target.value) {
        applyWorkerTemplate(e.target.value);
      }
    });
  }

  const needEnableCheckbox = document.getElementById("worker-field-need-enable");
  if (needEnableCheckbox) {
    needEnableCheckbox.addEventListener("change", (e) => {
      document.getElementById("worker-enable-fields").classList.toggle("hidden", !e.target.checked);
    });
  }
});

window.workersModule = {
  openWorkersDialog,
  closeWorkersDialog,
  loadWorkersTable
};
