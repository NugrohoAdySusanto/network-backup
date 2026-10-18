// Users / Preferences Dialog Logic

let currentUsersList = [];

async function openPreferencesDialog() {
  const currentUser = window.authModule.currentUser();
  if (!currentUser) return;

  document.getElementById("current-user-display").textContent = currentUser.username;
  
  const roleBadge = document.getElementById("current-user-role-badge");
  roleBadge.textContent = (currentUser.role || 'viewer').toUpperCase();

  if (currentUser.role === "admin") {
    roleBadge.className = "font-mono text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border border-purple-500/30 bg-purple-500/10 text-purple-600 dark:text-purple-400";
    document.getElementById("admin-user-management-section").classList.remove("hidden");
    document.getElementById("visitor-user-notice").classList.add("hidden");
    await renderUserListTable();
  } else {
    roleBadge.className = "font-mono text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border border-sky-500/30 bg-sky-500/10 text-sky-600 dark:text-sky-400";
    document.getElementById("admin-user-management-section").classList.add("hidden");
    document.getElementById("visitor-user-notice").classList.remove("hidden");
  }

  // Reset Form fields
  document.getElementById("old-password").value = "";
  document.getElementById("new-password").value = "";
  document.getElementById("confirm-password").value = "";
  document.getElementById("new-user-name").value = "";
  const emailInput = document.getElementById("new-user-email");
  if (emailInput) emailInput.value = "";
  document.getElementById("new-user-pass").value = "";
  const roleSelect = document.getElementById("new-user-role");
  if (roleSelect) roleSelect.value = "viewer";
  hideAccountAlert();

  window.openDialog(document.getElementById("preferences-dialog"), document.getElementById("old-password"));
}

function showAccountAlert(message, isSuccess = true) {
  const alertBox = document.getElementById("account-alert");
  if (!alertBox) return;
  alertBox.textContent = message;
  alertBox.classList.remove("hidden");
  if (isSuccess) {
    alertBox.className = "rounded-xl p-3 text-xs font-semibold border border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400";
  } else {
    alertBox.className = "rounded-xl p-3 text-xs font-semibold border border-red-500/30 bg-red-500/10 text-red-600 dark:text-red-400";
  }
}

function hideAccountAlert() {
  const alertBox = document.getElementById("account-alert");
  if (alertBox) alertBox.classList.add("hidden");
}

async function renderUserListTable() {
  try {
    const res = await window.api.users.list();
    const rawItems = res?.items || [];
    
    // Filter active users only (soft-deleted / deactivated users are excluded)
    currentUsersList = rawItems.filter(u => u.is_active !== false);
    
    const tbody = document.getElementById("user-list-tbody");
    tbody.innerHTML = "";
    
    const currentUser = window.authModule.currentUser();

    currentUsersList.forEach(u => {
      const tr = document.createElement("tr");
      tr.className = "hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors";
      
      const isCurrent = currentUser && (u.username.toLowerCase() === currentUser.username.toLowerCase());
      const isLastAdmin = (u.role === "admin" && currentUsersList.filter(x => x.role === "admin").length <= 1);
      const canDelete = !isCurrent && !isLastAdmin;

      const isViewer = u.role === "viewer" || u.role === "visitor";
      const badgeRoleLabel = isViewer ? "Viewer" : "Admin";
      const badgeClass = isViewer
        ? "border-sky-500/30 bg-sky-500/10 text-sky-600 dark:text-sky-400"
        : "border-purple-500/30 bg-purple-500/10 text-purple-600 dark:text-purple-400";

      tr.innerHTML = `
        <td class="py-2.5 px-3.5">
          <span class="font-bold text-xs">${u.username}</span>
          ${isCurrent ? '<span class="ml-1 text-[10px] text-sky-500 font-mono font-medium">(You)</span>' : ''}
        </td>
        <td class="py-2.5 px-3.5">
          <span class="text-xs muted font-mono">${u.email || '<span class="italic opacity-50">none</span>'}</span>
        </td>
        <td class="py-2.5 px-3.5">
          <span class="font-mono text-[10px] uppercase font-bold px-2 py-0.5 rounded-full border ${badgeClass}">
            ${badgeRoleLabel}
          </span>
        </td>
        <td class="py-2.5 px-3.5 text-emerald-600 dark:text-emerald-400 font-semibold text-[11px]">
          Active
        </td>
        <td class="py-2.5 px-3.5 text-right">
          <button type="button" 
            class="remove-user-btn rounded-lg w-7 h-7 inline-flex items-center justify-center transition-colors ${canDelete ? 'text-red-500 hover:bg-red-500/10 hover:text-red-600' : 'text-slate-300 dark:text-slate-600 cursor-not-allowed opacity-30'}"
            title="${canDelete ? 'Delete User' : (isCurrent ? 'Cannot delete your own active account' : 'Cannot delete the last remaining admin')}"
            ${!canDelete ? 'disabled' : ''}
            onclick="handleDeleteUser('${u.id}', '${u.username}')">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </td>
      `;
      tbody.appendChild(tr);
    });

    const badge = document.getElementById("user-count-badge");
    if (badge) {
      badge.textContent = `${currentUsersList.length} ${currentUsersList.length === 1 ? 'user' : 'users'}`;
    }

  } catch (err) {
    showAccountAlert("Failed to load users: " + err.message, false);
  }
}

window.handleDeleteUser = async function(userId, username) {
  const displayName = username || `User #${userId}`;
  if (!confirm(`Are you sure you want to delete user "${displayName}"?`)) {
    return;
  }
  try {
    await window.api.users.delete(userId);
    showAccountAlert(`User "${displayName}" deleted successfully.`, true);
    await renderUserListTable();
  } catch (err) {
    showAccountAlert("Failed to delete user: " + err.message, false);
  }
};

document.addEventListener("DOMContentLoaded", () => {
  const adminBtn = document.getElementById("admin-btn");
  const adminMenu = document.getElementById("admin-menu");
  if (adminBtn && adminMenu) {
    adminBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      window.toggleMenu(adminBtn, adminMenu);
    });
  }

  const prefBtn = document.getElementById("preferences-btn");
  if (prefBtn) {
    prefBtn.addEventListener("click", () => {
      window.closeMenus();
      openPreferencesDialog();
    });
  }

  const cancelBtn = document.getElementById("preferences-cancel-btn");
  if (cancelBtn) {
    cancelBtn.addEventListener("click", () => {
      window.closeDialog(document.getElementById("preferences-dialog"));
    });
  }

  const closeX = document.getElementById("preferences-close-x");
  if (closeX) {
    closeX.addEventListener("click", () => {
      window.closeDialog(document.getElementById("preferences-dialog"));
    });
  }

  const savePassDirectBtn = document.getElementById("save-password-direct-btn");
  if (savePassDirectBtn) {
    savePassDirectBtn.addEventListener("click", async () => {
      const oldPass = document.getElementById("old-password").value;
      const newPass = document.getElementById("new-password").value;
      const confirmPass = document.getElementById("confirm-password").value;

      if (!oldPass || !newPass || !confirmPass) {
        showAccountAlert("Harap isi semua kolom password (Password lama, baru, dan konfirmasi).", false);
        return;
      }

      try {
        savePassDirectBtn.disabled = true;
        savePassDirectBtn.textContent = "Menyimpan...";
        await window.api.auth.changePassword(oldPass, newPass, confirmPass);
        showAccountAlert("Password berhasil diubah.", true);
        if (window.inform) window.inform("Password changed successfully.");
        document.getElementById("old-password").value = "";
        document.getElementById("new-password").value = "";
        document.getElementById("confirm-password").value = "";
      } catch (err) {
        showAccountAlert(err.message, false);
      } finally {
        savePassDirectBtn.disabled = false;
        savePassDirectBtn.innerHTML = `
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
          </svg>
          <span>Simpan Password</span>
        `;
      }
    });
  }

  const saveBtn = document.getElementById("preferences-save-btn");
  if (saveBtn) {
    saveBtn.addEventListener("click", async () => {
      const oldPass = document.getElementById("old-password").value;
      const newPass = document.getElementById("new-password").value;
      const confirmPass = document.getElementById("confirm-password").value;

      if (oldPass || newPass || confirmPass) {
        try {
          await window.api.auth.changePassword(oldPass, newPass, confirmPass);
          if (window.inform) window.inform("Password changed successfully.");
          window.closeDialog(document.getElementById("preferences-dialog"));
        } catch (err) {
          showAccountAlert(err.message, false);
        }
      } else {
        window.closeDialog(document.getElementById("preferences-dialog"));
      }
    });
  }

  const addUserBtn = document.getElementById("add-user-btn");
  if (addUserBtn) {
    addUserBtn.addEventListener("click", async () => {
      const username = document.getElementById("new-user-name").value.trim();
      const emailField = document.getElementById("new-user-email");
      const email = emailField ? emailField.value.trim() || null : null;
      const password = document.getElementById("new-user-pass").value.trim();
      const role = document.getElementById("new-user-role").value;

      if (!username || !password) {
        showAccountAlert("Please provide both username and password.", false);
        return;
      }

      if (email && (!email.includes("@") || !email.includes("."))) {
        showAccountAlert("Please provide a valid email address.", false);
        return;
      }

      const originalBtnHtml = addUserBtn.innerHTML;
      try {
        addUserBtn.disabled = true;
        addUserBtn.innerHTML = `<span>Adding...</span>`;
        await window.api.users.create(username, password, role, email);
        showAccountAlert(`User "${username}" created successfully.`, true);
        document.getElementById("new-user-name").value = "";
        if (emailField) emailField.value = "";
        document.getElementById("new-user-pass").value = "";
        await renderUserListTable();
      } catch (err) {
        showAccountAlert("Failed to create user: " + err.message, false);
      } finally {
        addUserBtn.disabled = false;
        addUserBtn.innerHTML = originalBtnHtml;
      }
    });
  }
});
