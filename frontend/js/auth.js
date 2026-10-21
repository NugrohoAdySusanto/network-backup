// Authentication Logic
let currentUser = null;

function showDashboard() {
  const dashboard = document.getElementById("main-dashboard-app");
  if (dashboard) {
    dashboard.classList.remove("hidden");
  }
  const loginModal = document.getElementById("login-modal");
  if (loginModal) {
    loginModal.classList.add("hidden");
    loginModal.classList.remove("flex");
  }
  const forgotModal = document.getElementById("forgot-password-modal");
  if (forgotModal) {
    forgotModal.classList.add("hidden");
    forgotModal.classList.remove("flex");
  }
  const resetModal = document.getElementById("reset-password-modal");
  if (resetModal) {
    resetModal.classList.add("hidden");
    resetModal.classList.remove("flex");
  }
}

function hideDashboard() {
  const dashboard = document.getElementById("main-dashboard-app");
  if (dashboard) {
    dashboard.classList.add("hidden");
  }
}

async function checkAuthStatus() {
  try {
    const user = await window.api.auth.me();
    currentUser = user.user;
    if (user.csrf_token) {
      localStorage.setItem("nb_csrf_token", user.csrf_token);
    }
    
    // User is authenticated, update UI
    showDashboard();
    
    // Update Header
    // Apply role-based UI restrictions
    applyRolePermissions();
    
    // Load devices after auth
    if (window.devicesModule && window.devicesModule.loadDevices) {
      window.devicesModule.loadDevices();
    }
    
    return true;
  } catch (error) {
    // Not authenticated or error
    currentUser = null;
    hideDashboard();
    document.getElementById("login-modal").classList.remove("hidden");
    document.getElementById("login-modal").classList.add("flex");
    return false;
  }
}

function applyRolePermissions() {
  if (!currentUser) return;
  const isAdmin = currentUser.role === 'admin';
  const roleTitle = isAdmin ? 'Admin' : 'Viewer';
  const labelEl = document.getElementById("header-user-label");
  if (labelEl) labelEl.textContent = `${roleTitle} (${currentUser.username})`;

  const iconEl = document.getElementById("header-user-role-icon");
  if (iconEl) {
    if (isAdmin) {
      iconEl.classList.replace("bg-amber-500", "bg-emerald-500");
    } else {
      iconEl.classList.replace("bg-emerald-500", "bg-amber-500");
    }
  }

  // Toggle visibility of all admin-only elements across the app
  document.querySelectorAll(".admin-only-feature").forEach(el => {
    if (isAdmin) {
      el.classList.remove("hidden");
      el.style.display = "";
    } else {
      el.classList.add("hidden");
      el.style.display = "none";
    }
  });
}

async function handleLoginSubmit(event) {
  event.preventDefault();
  
  const usernameInput = document.getElementById("login-username").value;
  const passwordInput = document.getElementById("login-password").value;
  const rememberMe = document.getElementById("remember-me").checked;
  const errorAlert = document.getElementById("login-error");
  const submitBtn = document.getElementById("login-submit-btn");
  
  submitBtn.disabled = true;
  errorAlert.classList.add("hidden");
  
  try {
    const response = await window.api.auth.login(usernameInput, passwordInput, rememberMe);
    
    if (response.csrf_token) {
      localStorage.setItem("nb_csrf_token", response.csrf_token);
    }
    currentUser = response.user;
    
    // Switch to Dashboard
    showDashboard();
    
    // Update Header & Role-based UI
    applyRolePermissions();
    
    // Load devices
    if (window.devicesModule && window.devicesModule.loadDevices) {
      window.devicesModule.loadDevices();
    }
    
  } catch (error) {
    errorAlert.textContent = error.message || "Invalid username or password.";
    errorAlert.classList.remove("hidden");
  } finally {
    submitBtn.disabled = false;
  }
}

async function handleLogout() {
  try {
    await window.api.auth.logout();
  } catch (e) {
    console.error("Logout failed", e);
  } finally {
    currentUser = null;
    hideDashboard();
    localStorage.removeItem("nb_csrf_token");
    window.location.reload();
  }
}

function togglePasswordVisibility() {
  const input = document.getElementById("login-password");
  const btn = document.getElementById("toggle-password-btn");
  if (input.type === "password") {
    input.type = "text";
    btn.classList.add("text-sky-500");
  } else {
    input.type = "password";
    btn.classList.remove("text-sky-500");
  }
}

// Forgot Password & Reset Password Modals
function openForgotPasswordModal() {
  hideDashboard();
  document.getElementById("login-modal").classList.add("hidden");
  document.getElementById("login-modal").classList.remove("flex");

  const modal = document.getElementById("forgot-password-modal");
  modal.classList.remove("hidden");
  modal.classList.add("flex");
  
  const alertBox = document.getElementById("forgot-alert");
  if (alertBox) alertBox.classList.add("hidden");
  const emailInput = document.getElementById("forgot-email");
  if (emailInput) {
    emailInput.value = "";
    emailInput.focus();
  }
}

function closeForgotPasswordModal() {
  hideDashboard();
  const modal = document.getElementById("forgot-password-modal");
  modal.classList.add("hidden");
  modal.classList.remove("flex");

  document.getElementById("login-modal").classList.remove("hidden");
  document.getElementById("login-modal").classList.add("flex");
}

async function handleForgotPasswordSubmit(event) {
  event.preventDefault();
  const email = (document.getElementById("forgot-email")?.value || "").trim();
  const alertBox = document.getElementById("forgot-alert");
  const submitBtn = document.getElementById("forgot-submit-btn");

  if (!email) return;

  if (!email.includes("@") || !email.includes(".")) {
    alertBox.className = "rounded-lg p-3 text-xs font-semibold border border-red-500/30 bg-red-500/10 text-red-600 dark:text-red-400";
    alertBox.textContent = "Please enter a valid email address (e.g. user@makuku.co.id).";
    alertBox.classList.remove("hidden");
    return;
  }

  submitBtn.disabled = true;
  submitBtn.innerHTML = `<span>Sending Email...</span>`;
  alertBox.classList.add("hidden");

  try {
    const res = await window.api.auth.forgotPassword(email);
    alertBox.className = "rounded-lg p-3 text-xs font-semibold border border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400";
    alertBox.textContent = res?.message || "If the email address is registered, a password recovery link has been sent to your email.";
    alertBox.classList.remove("hidden");
    const emailInput = document.getElementById("forgot-email");
    if (emailInput) emailInput.value = "";
  } catch (err) {
    alertBox.className = "rounded-lg p-3 text-xs font-semibold border border-red-500/30 bg-red-500/10 text-red-600 dark:text-red-400";
    alertBox.textContent = err.message || "Failed to send password reset email.";
    alertBox.classList.remove("hidden");
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerHTML = `<span>Send Reset Link</span><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3" /></svg>`;
  }
}

function openResetPasswordModal(token) {
  hideDashboard();
  document.getElementById("login-modal").classList.add("hidden");
  document.getElementById("login-modal").classList.remove("flex");

  const modal = document.getElementById("reset-password-modal");
  modal.classList.remove("hidden");
  modal.classList.add("flex");

  document.getElementById("reset-token-input").value = token;
  document.getElementById("reset-new-password").value = "";
  document.getElementById("reset-confirm-password").value = "";
  
  const alertBox = document.getElementById("reset-alert");
  if (alertBox) alertBox.classList.add("hidden");
  document.getElementById("reset-new-password").focus();
}

function closeResetPasswordModal() {
  hideDashboard();
  const modal = document.getElementById("reset-password-modal");
  modal.classList.add("hidden");
  modal.classList.remove("flex");

  if (window.location.hash.includes("reset-password")) {
    history.replaceState(null, "", window.location.pathname);
  }

  document.getElementById("login-modal").classList.remove("hidden");
  document.getElementById("login-modal").classList.add("flex");
}

async function handleResetPasswordSubmit(event) {
  event.preventDefault();
  const token = document.getElementById("reset-token-input").value.trim();
  const newPass = document.getElementById("reset-new-password").value;
  const confirmPass = document.getElementById("reset-confirm-password").value;
  const alertBox = document.getElementById("reset-alert");
  const submitBtn = document.getElementById("reset-submit-btn");

  if (!token) {
    alertBox.className = "rounded-lg p-3 text-xs font-semibold border border-red-500/30 bg-red-500/10 text-red-600 dark:text-red-400";
    alertBox.textContent = "Reset token not found or invalid.";
    alertBox.classList.remove("hidden");
    return;
  }

  if (newPass !== confirmPass) {
    alertBox.className = "rounded-lg p-3 text-xs font-semibold border border-red-500/30 bg-red-500/10 text-red-600 dark:text-red-400";
    alertBox.textContent = "New password confirmation does not match.";
    alertBox.classList.remove("hidden");
    return;
  }

  submitBtn.disabled = true;
  submitBtn.textContent = "Saving New Password...";
  alertBox.classList.add("hidden");

  try {
    const res = await window.api.auth.resetPassword(token, newPass, confirmPass);
    alertBox.className = "rounded-lg p-3 text-xs font-semibold border border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400";
    alertBox.textContent = (res?.message || "Password changed successfully!") + " Redirecting to login...";
    alertBox.classList.remove("hidden");

    setTimeout(() => {
      closeResetPasswordModal();
    }, 2000);
  } catch (err) {
    alertBox.className = "rounded-lg p-3 text-xs font-semibold border border-red-500/30 bg-red-500/10 text-red-600 dark:text-red-400";
    alertBox.textContent = err.message || "Failed to reset password.";
    alertBox.classList.remove("hidden");
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Save New Password";
  }
}

// Attach events
document.addEventListener("DOMContentLoaded", () => {
  const loginForm = document.getElementById("login-form");
  if (loginForm) {
    loginForm.addEventListener("submit", handleLoginSubmit);
  }
  
  const logoutBtn = document.getElementById("logout-btn");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", handleLogout);
  }

  // Check URL hash/query for reset-password token
  const hash = window.location.hash || "";
  const query = window.location.search || "";
  let resetToken = null;
  if (hash.includes("token=")) {
    resetToken = new URLSearchParams(hash.split("?")[1] || "").get("token");
  } else if (query.includes("token=")) {
    resetToken = new URLSearchParams(query).get("token");
  }
  if (resetToken) {
    openResetPasswordModal(resetToken);
  } else {
    // Initial check
    checkAuthStatus();
  }
});

window.authModule = {
  currentUser: () => currentUser,
  checkAuthStatus,
  showDashboard,
  hideDashboard,
  handleLogout,
  togglePasswordVisibility,
  openForgotPasswordModal,
  closeForgotPasswordModal,
  openResetPasswordModal,
  closeResetPasswordModal,
};
