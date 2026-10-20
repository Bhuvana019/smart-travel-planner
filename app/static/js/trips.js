/**
 * ============================================================================
 * SMART TRAVEL PLANNER - TRIPS & TRIP DETAILS CONTROLLER
 * Real FastAPI Backend Data Binding
 * ============================================================================
 */

let currentLoadedTrip = null;

document.addEventListener("DOMContentLoaded", () => {
  const createForm = document.getElementById("create-trip-form");
  if (createForm) {
    setupCreateTripForm(createForm);
  }

  const tripDetailsHero = document.getElementById("trip-details-container");
  if (tripDetailsHero) {
    loadTripDetails();
    setupEditTripForm();
  }
});

function setupCreateTripForm(form) {
  const destInput = document.getElementById("destination");
  const startInput = document.getElementById("start_date");
  const endInput = document.getElementById("end_date");
  const travellersInput = document.getElementById("travellers");
  const budgetInput = document.getElementById("budget");
  const descInput = document.getElementById("description");

  // Real-time error clearing
  [destInput, startInput, endInput, travellersInput, budgetInput].forEach(input => {
    if (input) {
      input.addEventListener("input", () => Validator.clearFieldError(input));
    }
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    let isValid = true;

    // 1. Destination
    if (!destInput.value.trim()) {
      Validator.setFieldError(destInput, "Destination is required");
      isValid = false;
    }

    // 2. Start date
    if (!startInput.value) {
      Validator.setFieldError(startInput, "Start date is required");
      isValid = false;
    }

    // 3. End date
    if (!endInput.value) {
      Validator.setFieldError(endInput, "End date is required");
      isValid = false;
    }

    // 4. End date >= Start date
    if (startInput.value && endInput.value) {
      const start = new Date(startInput.value);
      const end = new Date(endInput.value);
      if (end < start) {
        Validator.setFieldError(endInput, "End date must be on or after start date");
        isValid = false;
      }
    }

    // 5. Travelers > 0
    const travellers = parseInt(travellersInput.value, 10);
    if (isNaN(travellers) || travellers <= 0) {
      Validator.setFieldError(travellersInput, "Must have at least 1 traveler");
      isValid = false;
    }

    // 6. Budget >= 2000
    const budget = typeof parseBudgetInput === "function" ? parseBudgetInput(budgetInput.value) : parseFloat(budgetInput.value);
    if (isNaN(budget) || budget < 2000) {
      Validator.setFieldError(budgetInput, "Budget must be at least ₹2,000 (e.g. 25000, 25,000, 25k)");
      isValid = false;
    }

    if (!isValid) {
      showToast("Please correct the form errors before submitting", "error");
      return;
    }

    // Gather selected interest tags
    const checkedInterests = [];
    document.querySelectorAll('input[name="interests"]:checked').forEach(cb => {
      checkedInterests.push(cb.value);
    });

    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = `<span class="spinner"></span> Creating Trip...`;

    const nameInput = document.getElementById("trip_name");
    const tripData = {
      trip_name: nameInput && nameInput.value.trim() ? nameInput.value.trim() : destInput.value.trim(),
      destination: destInput.value.trim(),
      start_date: startInput.value,
      end_date: endInput.value,
      travellers: travellers,
      budget: budget,
      interests: checkedInterests.join(", "),
      description: descInput ? descInput.value.trim() : ""
    };

    try {
      const newTrip = await ApiService.trips.create(tripData);
      showToast(`Trip to ${newTrip.destination} created successfully!`, "success");
      
      // Permanently set as active workspace trip across all modules
      if (typeof setActiveTrip === "function") {
        setActiveTrip(newTrip.trip_id, newTrip.destination, newTrip);
      } else {
        localStorage.setItem("active_trip_id", String(newTrip.trip_id));
        localStorage.setItem("active_trip_destination", newTrip.destination);
        try {
          localStorage.setItem("active_trip_meta", JSON.stringify(newTrip));
        } catch (e) {}
      }

      setTimeout(() => {
        window.location.href = `trip.html?id=${newTrip.trip_id}`;
      }, 700);
    } catch (err) {
      showToast(err.message || "Failed to create trip", "error");
      submitBtn.disabled = false;
      submitBtn.innerHTML = originalText;
    }
  });
}

async function loadTripDetails() {
  const urlParams = new URLSearchParams(window.location.search);
  const paramId = urlParams.get("id");
  let tripId = (paramId && !isNaN(parseInt(paramId, 10)) && parseInt(paramId, 10) !== 101)
    ? parseInt(paramId, 10)
    : ((typeof getActiveTripId === "function" && getActiveTripId() && getActiveTripId() !== 101) ? getActiveTripId() : 130);

  try {
    const trip = await ApiService.trips.get(tripId);
    currentLoadedTrip = trip;
    
    // Synchronize active trip globally
    if (typeof setActiveTrip === "function") {
      setActiveTrip(trip.trip_id, trip.destination, trip);
    }

    renderTripHero(trip);
    renderTripBudgetOverview(trip);
    renderTripItineraryOverview(trip.itinerary_items || []);
    renderTripSavedExperiences(trip.saved_experiences || []);
  } catch (err) {
    console.warn("API trip load failed for trip ID", tripId, err);
    if (typeof ApiService !== "undefined" && ApiService.trips) {
      try {
        const trips = await ApiService.trips.list();
        if (trips && trips.length > 0) {
          const fallbackTrip = trips.find(t => t.trip_id === tripId) || trips.find(t => (t.destination || '').toLowerCase().includes("mysur")) || trips[trips.length - 1];
          currentLoadedTrip = fallbackTrip;
          if (typeof setActiveTrip === "function") {
            setActiveTrip(fallbackTrip.trip_id, fallbackTrip.destination, fallbackTrip);
          }
          renderTripHero(fallbackTrip);
          renderTripBudgetOverview(fallbackTrip);
          renderTripItineraryOverview(fallbackTrip.itinerary_items || []);
          renderTripSavedExperiences(fallbackTrip.saved_experiences || []);
          return;
        }
      } catch (e2) {}
    }
  }
}

function renderTripHero(trip) {
  const titleElem = document.getElementById("trip-dest-title");
  const datesElem = document.getElementById("trip-dates-text");
  const travellersElem = document.getElementById("trip-travellers-text");
  const budgetHeroElem = document.getElementById("trip-budget-hero");
  const statusBadge = document.getElementById("trip-status-badge");
  const heroBanner = document.getElementById("trip-hero-banner");

  if (titleElem) {
    if (trip.trip_name && trip.trip_name !== trip.destination) {
      titleElem.textContent = `${trip.trip_name} — ${trip.destination}`;
    } else {
      titleElem.textContent = trip.destination;
    }
  }
  if (datesElem) datesElem.textContent = `${formatDateDisplay(trip.start_date)} – ${formatDateDisplay(trip.end_date)}`;
  if (travellersElem) travellersElem.textContent = `${trip.travellers} Travelers`;
  if (budgetHeroElem) budgetHeroElem.textContent = formatINR(trip.budget);

  if (statusBadge) {
    if (trip.budget_exceeded) {
      statusBadge.textContent = "Budget Exceeded";
      statusBadge.className = "badge badge-danger";
    } else {
      statusBadge.textContent = trip.interests ? trip.interests.split(",")[0] : "Active";
      statusBadge.className = "badge badge-success";
    }
  }

  // Toggle Demo Badge - only show for trip 101
  const demoPill = document.getElementById("trip-demo-pill") || document.querySelector(".demo-badge-pill");
  if (demoPill) {
    demoPill.style.display = (Number(trip.trip_id) === 101) ? "inline-block" : "none";
  }

  // Set theme on hero banner
  if (heroBanner) {
    const destLower = (trip.destination || "").toLowerCase();
    heroBanner.className = "trip-hero " + (
      destLower.includes("kerala") || destLower.includes("munnar") ? "kerala-theme" :
      destLower.includes("ladakh") || destLower.includes("manali") ? "ladakh-theme" :
      "goa-theme"
    );
  }

  // Set Featured recommendations header title
  const recsHeader = document.getElementById("overview-recs-header-title");
  if (recsHeader) {
    recsHeader.textContent = `Featured for ${trip.destination}`;
  }

  // Update trip subnavigation & action links with active trip id
  document.querySelectorAll('a[href*="itinerary.html"]').forEach(link => {
    link.setAttribute("href", `itinerary.html?id=${trip.trip_id}`);
  });
  document.querySelectorAll('a[href*="expenses.html"]').forEach(link => {
    link.setAttribute("href", `expenses.html?id=${trip.trip_id}`);
  });
  document.querySelectorAll('a[href*="recommendations.html"]').forEach(link => {
    link.setAttribute("href", `recommendations.html?id=${trip.trip_id}`);
  });
}

function renderTripBudgetOverview(trip) {
  const spent = Number(trip.total_spent) || 0;
  const budget = Number(trip.budget) || 0;
  const remaining = Math.max(0, budget - spent);
  const percentage = budget > 0 ? Math.min(100, Math.round((spent / budget) * 100)) : 0;

  const spentElem = document.getElementById("overview-spent-val");
  const remainingElem = document.getElementById("overview-remaining-val");
  const barElem = document.getElementById("overview-budget-bar");
  const percentText = document.getElementById("overview-budget-pct");
  const targetElem = document.getElementById("overview-budget-target");

  if (spentElem) spentElem.textContent = formatINR(spent);
  if (remainingElem) remainingElem.textContent = formatINR(remaining);
  if (percentText) percentText.textContent = `${percentage}% of budget spent`;
  if (targetElem) targetElem.textContent = `Target: ${formatINR(budget)}`;

  if (barElem) {
    barElem.style.width = `${percentage}%`;
    barElem.className = `progress-bar-fill ${trip.budget_exceeded ? 'fill-danger' : percentage > 70 ? 'fill-warn' : 'fill-safe'}`;
  }
}

function renderTripItineraryOverview(items) {
  const listContainer = document.getElementById("overview-itinerary-list");
  if (!listContainer) return;

  const displayItems = items.slice(0, 3);
  if (displayItems.length === 0) {
    listContainer.innerHTML = `
      <div class="empty-state" style="padding: 1.5rem;">
        <p style="color: var(--text-muted); font-size: 0.9rem;">No itinerary activities scheduled yet.</p>
      </div>
    `;
    return;
  }

  listContainer.innerHTML = displayItems.map(item => `
    <div class="itinerary-card" style="margin-bottom: 0.75rem;">
      <div class="itinerary-details">
        <span class="itinerary-activity-name">${item.activity}</span>
        <div class="itinerary-meta">
          <span>🕒 ${item.time}</span>
          <span>📍 ${item.location || 'General'}</span>
          <span>💰 ${item.estimated_cost > 0 ? formatINR(item.estimated_cost) : 'Free'}</span>
        </div>
      </div>
    </div>
  `).join("");
}

function renderTripSavedExperiences(savedList) {
  const container = document.getElementById("overview-recs-list");
  if (!container) return;

  if (savedList.length === 0) {
    container.innerHTML = `
      <div style="text-align: center; padding: 1.5rem; color: var(--text-muted); font-size: 0.85rem;">
        No experiences saved from Experience Finder yet.
      </div>
    `;
    return;
  }

  container.innerHTML = savedList.map(rec => `
    <div class="card" style="margin-bottom: 0.75rem;">
      <div class="card-body" style="padding: 0.85rem 1rem; display: flex; justify-content: space-between; align-items: center;">
        <div>
          <div style="font-weight: 700; font-size: 0.95rem;">${rec.name}</div>
          <div style="font-size: 0.8rem; color: var(--text-muted);">${rec.category} • ⭐ ${rec.rating}</div>
        </div>
        <div style="text-align: right;">
          <div style="font-weight: 700; color: var(--primary); font-size: 0.95rem;">
            ${rec.price > 0 ? formatINR(rec.price) : 'Free'}
          </div>
          <span class="badge badge-success" style="font-size: 0.7rem;">Saved</span>
        </div>
      </div>
    </div>
  `).join("");
}

function openEditTripModal() {
  if (!currentLoadedTrip) return;
  const nameElem = document.getElementById("edit-trip-name");
  const destElem = document.getElementById("edit-trip-dest");
  const startElem = document.getElementById("edit-trip-start");
  const endElem = document.getElementById("edit-trip-end");
  const travElem = document.getElementById("edit-trip-travellers");
  const budgetElem = document.getElementById("edit-trip-budget");
  const intElem = document.getElementById("edit-trip-interests");
  const descElem = document.getElementById("edit-trip-desc");

  if (nameElem) nameElem.value = currentLoadedTrip.trip_name || currentLoadedTrip.destination || "";
  if (destElem) destElem.value = currentLoadedTrip.destination || "";
  if (startElem) startElem.value = currentLoadedTrip.start_date || "";
  if (endElem) endElem.value = currentLoadedTrip.end_date || "";
  if (travElem) travElem.value = currentLoadedTrip.travellers || 1;
  if (budgetElem) budgetElem.value = currentLoadedTrip.budget || "";
  if (intElem) intElem.value = currentLoadedTrip.interests || "";
  if (descElem) descElem.value = currentLoadedTrip.description || "";

  openModal("edit-trip-modal");
}

function setupEditTripForm() {
  const form = document.getElementById("edit-trip-form");
  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!currentLoadedTrip) return;

    const tripName = document.getElementById("edit-trip-name") ? document.getElementById("edit-trip-name").value.trim() : "";
    const dest = document.getElementById("edit-trip-dest").value.trim();
    const start = document.getElementById("edit-trip-start").value;
    const end = document.getElementById("edit-trip-end").value;
    const travellers = parseInt(document.getElementById("edit-trip-travellers").value, 10);
    const budgetRaw = document.getElementById("edit-trip-budget").value;
    const budget = typeof parseBudgetInput === "function" ? parseBudgetInput(budgetRaw) : parseFloat(budgetRaw);
    const interests = document.getElementById("edit-trip-interests").value.trim();
    const desc = document.getElementById("edit-trip-desc").value.trim();

    if (!dest) {
      showToast("Destination is required", "error");
      return;
    }
    if (end < start) {
      showToast("End date must be on or after start date", "error");
      return;
    }
    if (isNaN(budget) || budget < 2000) {
      showToast("Budget must be at least ₹2,000 (e.g. 25000, 25,000, 25k)", "error");
      return;
    }

    const updatePayload = {
      trip_name: tripName || dest,
      destination: dest,
      start_date: start,
      end_date: end,
      travellers: travellers,
      budget: budget,
      interests: interests,
      description: desc
    };

    const submitBtn = form.querySelector('button[type="submit"]');
    const origText = submitBtn.textContent;
    submitBtn.disabled = true;
    submitBtn.textContent = "Saving...";

    try {
      await ApiService.trips.update(currentLoadedTrip.trip_id, updatePayload);
      showToast("Trip details updated successfully!", "success");
      closeModal("edit-trip-modal");
      await loadTripDetails();
    } catch (err) {
      showToast(err.message || "Failed to update trip", "error");
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = origText;
    }
  });
}

async function handleDeleteCurrentTrip() {
  if (!currentLoadedTrip) return;
  if (confirm(`Are you sure you want to permanently delete the "${currentLoadedTrip.destination}" trip and all its records?`)) {
    try {
      await ApiService.trips.delete(currentLoadedTrip.trip_id);
      showToast("Trip deleted successfully", "warning");
      setTimeout(() => {
        window.location.href = "dashboard.html";
      }, 500);
    } catch (err) {
      showToast(err.message || "Failed to delete trip", "error");
    }
  }
}
