/**
 * ============================================================================
 * SMART TRAVEL PLANNER - USER PROFILE & SETTINGS CONTROLLER
 * Real FastAPI Backend Integration (GET /api/users/me, PUT /api/users/me)
 * ============================================================================
 */

document.addEventListener("DOMContentLoaded", async () => {
  // 1. Ensure private page authentication
  if (!ApiService.auth.requireAuth()) {
    return;
  }

  const nameInput = document.getElementById("prof-name");
  const emailInput = document.getElementById("prof-email");
  const curPassInput = document.getElementById("prof-cur-password");
  const newPassInput = document.getElementById("prof-new-password");
  const currencyInput = document.getElementById("prof-currency");
  const phoneInput = document.getElementById("prof-phone");
  const bioInput = document.getElementById("prof-bio");
  const form = document.getElementById("profile-form");
  const saveBtn = document.getElementById("btn-save-profile");
  const logoutBtn = document.getElementById("btn-profile-logout");

  // DOM Display Elements
  const avatarDisplay = document.getElementById("profile-avatar-display");
  const nameDisplay = document.getElementById("profile-name-display");
  const emailDisplay = document.getElementById("profile-email-display");
  const tripsCountDisplay = document.getElementById("profile-trips-count");
  const createdDisplay = document.getElementById("profile-created-display");
  const sidebarAvatar = document.getElementById("sidebar-avatar");
  const sidebarUserName = document.getElementById("sidebar-user-name");

  // Helper to extract initials
  function getInitials(name) {
    if (!name) return "TP";
    const parts = name.trim().split(/\s+/);
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return name.slice(0, 2).toUpperCase();
  }

  // 2. Fetch and render real user profile from backend
  async function loadProfile() {
    try {
      const user = await ApiService.auth.getMe();
      if (!user) return;

      // Populate form
      if (nameInput) nameInput.value = user.name || "";
      if (emailInput) emailInput.value = user.email || "";

      // Populate displays
      const initials = getInitials(user.name);
      if (avatarDisplay) avatarDisplay.textContent = initials;
      if (nameDisplay) nameDisplay.textContent = user.name;
      if (emailDisplay) emailDisplay.textContent = user.email;

      if (sidebarAvatar) sidebarAvatar.textContent = initials;
      if (sidebarUserName) sidebarUserName.textContent = user.name;

      if (createdDisplay && user.created_at) {
        try {
          const d = new Date(user.created_at);
          createdDisplay.textContent = d.toLocaleDateString("en-US", {
            month: "short",
            year: "numeric"
          });
        } catch (e) {
          createdDisplay.textContent = "Oct 2026";
        }
      }

      // Load trip count from real API
      try {
        const trips = await ApiService.trips.list();
        if (tripsCountDisplay) {
          tripsCountDisplay.textContent = Array.isArray(trips) ? trips.length : "0";
        }
      } catch (e) {
        console.warn("Could not load trip count:", e);
      }

    } catch (err) {
      console.error("Failed to load user profile:", err);
      showToast("Session expired or invalid. Please sign in again.", "warning");
      setTimeout(() => {
        ApiService.auth.logout();
      }, 1200);
    }
  }

  await loadProfile();

  // 3. Clear errors on input change
  if (nameInput) nameInput.addEventListener("input", () => Validator.clearFieldError(nameInput));
  if (emailInput) emailInput.addEventListener("input", () => Validator.clearFieldError(emailInput));
  if (curPassInput) curPassInput.addEventListener("input", () => Validator.clearFieldError(curPassInput));
  if (newPassInput) newPassInput.addEventListener("input", () => Validator.clearFieldError(newPassInput));

  // 4. Handle Profile Form Submission (PUT /api/users/me)
  if (form) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      let isValid = true;

      const nameVal = nameInput ? nameInput.value.trim() : "";
      const emailVal = emailInput ? emailInput.value.trim() : "";
      const curPassVal = curPassInput ? curPassInput.value : "";
      const newPassVal = newPassInput ? newPassInput.value : "";

      if (!nameVal || nameVal.length < 2) {
        Validator.setFieldError(nameInput, "Please enter a valid name (at least 2 characters)");
        isValid = false;
      }

      if (!emailVal || !Validator.isValidEmail(emailVal)) {
        Validator.setFieldError(emailInput, "Please enter a valid email address");
        isValid = false;
      }

      if (newPassVal && newPassVal.length < 6) {
        Validator.setFieldError(newPassInput, "New password must be at least 6 characters");
        isValid = false;
      }

      if (newPassVal && !curPassVal) {
        Validator.setFieldError(curPassInput, "Current password required to set a new password");
        isValid = false;
      }

      if (!isValid) {
        showToast("Please correct the errors in the form", "error");
        return;
      }

      if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.innerHTML = `<span class="spinner"></span> Saving...`;
      }

      const payload = {
        name: nameVal,
        email: emailVal
      };

      if (newPassVal) {
        payload.current_password = curPassVal;
        payload.new_password = newPassVal;
      }

      try {
        const updatedUser = await ApiService.auth.updateProfile(payload);

        // Update displays in real time
        const initials = getInitials(updatedUser.name);
        if (avatarDisplay) avatarDisplay.textContent = initials;
        if (nameDisplay) nameDisplay.textContent = updatedUser.name;
        if (emailDisplay) emailDisplay.textContent = updatedUser.email;
        if (sidebarAvatar) sidebarAvatar.textContent = initials;
        if (sidebarUserName) sidebarUserName.textContent = updatedUser.name;

        // Clear password fields
        if (curPassInput) curPassInput.value = "";
        if (newPassInput) newPassInput.value = "";

        showToast("Profile settings saved successfully!", "success");
      } catch (err) {
        console.error("Profile update error:", err);
        const errMsg = err.message || "Failed to update profile";
        showToast(errMsg, "error");
        if (errMsg.toLowerCase().includes("email")) {
          Validator.setFieldError(emailInput, errMsg);
        } else if (errMsg.toLowerCase().includes("password")) {
          Validator.setFieldError(curPassInput, errMsg);
        }
      } finally {
        if (saveBtn) {
          saveBtn.disabled = false;
          saveBtn.textContent = "Save Changes";
        }
      }
    });
  }

  // 5. Handle Logout
  if (logoutBtn) {
    logoutBtn.addEventListener("click", async () => {
      if (confirm("Are you sure you want to sign out?")) {
        await ApiService.auth.logout();
      }
    });
  }

  // Attach global logout handler to any sidebar sign-out link
  document.querySelectorAll(".logout-trigger, [href='index.html'].sidebar-link").forEach(btn => {
    btn.addEventListener("click", async (e) => {
      e.preventDefault();
      await ApiService.auth.logout();
    });
  });
});
