/**
 * ============================================================================
 * SMART TRAVEL PLANNER - ITINERARY CONTROLLER
 * Real FastAPI Backend Data Binding with Full CRUD & Destination Alignment
 * ============================================================================
 */

let currentTripId = null;
let currentTripObj = null;
let cachedItineraryItems = [];
let userTripsList = [];
let editingItemId = null;

function escapeHtml(text) {
  if (!text) return "";
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

document.addEventListener("DOMContentLoaded", () => {
  initItineraryPage();
});

async function initItineraryPage() {
  const urlParams = new URLSearchParams(window.location.search);
  const paramId = urlParams.get("id");
  if (paramId && !isNaN(parseInt(paramId, 10)) && parseInt(paramId, 10) !== 101) {
    currentTripId = parseInt(paramId, 10);
  } else {
    const activeId = (typeof getActiveTripId === "function") ? getActiveTripId() : null;
    if (activeId && activeId !== 101) {
      currentTripId = activeId;
    } else {
      currentTripId = 130; // Mysuru default
    }
  }

  setupAddItineraryModal();
  setupAddActivityButtons();

  // Load user trips for dropdown selector and fallback
  await loadUserTripsForItinerary();
  await loadItineraryData();
}

async function loadUserTripsForItinerary() {
  try {
    if (typeof ApiService !== "undefined" && ApiService.trips) {
      userTripsList = await ApiService.trips.list();
    }
  } catch (err) {
    console.warn("Could not fetch user trips list:", err);
  }

  // Fallback to active trip meta if list is empty
  if (!userTripsList || userTripsList.length === 0) {
    const savedMeta = localStorage.getItem("active_trip_meta");
    if (savedMeta) {
      try {
        const metaObj = JSON.parse(savedMeta);
        if (metaObj && metaObj.trip_id) {
          userTripsList = [metaObj];
        }
      } catch (e) {}
    }
  }

  if (userTripsList && userTripsList.length > 0) {
    const activeStoredId = localStorage.getItem("active_trip_id");
    let match = null;
    if (currentTripId && currentTripId !== 101) {
      match = userTripsList.find(t => t.trip_id === currentTripId);
    }
    if (!match && activeStoredId && activeStoredId !== "101") {
      match = userTripsList.find(t => String(t.trip_id) === String(activeStoredId));
    }
    if (!match) {
      match = userTripsList.find(t => (t.destination || '').toLowerCase().includes("mysur")) || userTripsList[userTripsList.length - 1];
    }
    if (match) {
      currentTripId = match.trip_id;
      currentTripObj = match;
      if (typeof setActiveTrip === "function") {
        setActiveTrip(match.trip_id, match.destination, match);
      }
    }
    populateItineraryTripSelector(userTripsList);
  } else {
    populateItineraryTripSelector([]);
  }
}

function populateItineraryTripSelector(trips) {
  const select = document.getElementById("itinerary-trip-select");
  if (!select) return;

  if (!trips || trips.length === 0) {
    select.innerHTML = `<option value="130" selected>Mysuru (friends)</option>`;
    return;
  }

  select.innerHTML = trips.map(t => `
    <option value="${t.trip_id}" ${t.trip_id === currentTripId ? "selected" : ""}>
      ${escapeHtml(t.destination)} (${t.trip_name || 'Trip #' + t.trip_id})
    </option>
  `).join("");

  select.addEventListener("change", async (e) => {
    const selectedId = parseInt(e.target.value, 10);
    if (selectedId) {
      currentTripId = selectedId;
      const tripObj = userTripsList.find(t => t.trip_id === currentTripId);
      if (tripObj && typeof setActiveTrip === "function") {
        setActiveTrip(tripObj.trip_id, tripObj.destination, tripObj);
      }
      const url = new URL(window.location);
      url.searchParams.set("id", currentTripId);
      window.history.replaceState({}, "", url);
      await loadItineraryData();
    }
  });
}

function setupAddActivityButtons() {
  document.querySelectorAll('[onclick*="add-itinerary-modal"]').forEach(btn => {
    btn.addEventListener("click", () => {
      resetItineraryModalToAddMode();
    });
  });
}

function resetItineraryModalToAddMode() {
  editingItemId = null;
  const form = document.getElementById("add-itinerary-form");
  if (form) {
    form.reset();
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) submitBtn.textContent = "+ Add to Itinerary";
  }

  const catInput = document.getElementById("itinerary-category");
  if (catInput) catInput.value = "Sightseeing";

  const timeInput = document.getElementById("itinerary-time");
  if (timeInput) timeInput.value = "10:00";

  // Re-apply destination specific placeholders and dates
  if (currentTripObj) {
    applyDestinationModalCustomization(currentTripObj);
  }
}

async function loadItineraryData() {
  if (!currentTripId || currentTripId === 101) {
    const activeStoredId = localStorage.getItem("active_trip_id");
    if (activeStoredId && activeStoredId !== "101") {
      currentTripId = parseInt(activeStoredId, 10);
    } else if (userTripsList && userTripsList.length > 0) {
      const match = userTripsList.find(t => (t.destination || '').toLowerCase().includes("mysur")) || userTripsList[userTripsList.length - 1];
      currentTripId = match.trip_id;
    } else {
      currentTripId = 130;
    }
  }

  try {
    let trip = currentTripObj;
    if (!trip || trip.trip_id !== currentTripId) {
      trip = await ApiService.trips.get(currentTripId);
      currentTripObj = trip;
    }
    loadItineraryTripMeta(trip);

    const items = await ApiService.itinerary.list(currentTripId);
    cachedItineraryItems = items || [];
    renderItineraryList(cachedItineraryItems);

    // Fetch and display live recommended highlights from Experience Finder
    loadQuickRecommendations(trip);
  } catch (err) {
    console.warn("Failed to load itinerary for trip ID", currentTripId, err);
    if (userTripsList && userTripsList.length > 0) {
      const fallbackTrip = userTripsList.find(t => t.trip_id === currentTripId) || userTripsList.find(t => (t.destination || '').toLowerCase().includes("mysur")) || userTripsList[userTripsList.length - 1];
      currentTripId = fallbackTrip.trip_id;
      currentTripObj = fallbackTrip;
      loadItineraryTripMeta(fallbackTrip);
      try {
        const items = await ApiService.itinerary.list(currentTripId);
        cachedItineraryItems = items || [];
        renderItineraryList(cachedItineraryItems);
        loadQuickRecommendations(fallbackTrip);
      } catch (e2) {}
    }
  }
}

function loadItineraryTripMeta(trip) {
  const destElem = document.getElementById("itinerary-dest-title");
  const datesElem = document.getElementById("itinerary-dates-sub");
  const badgeElem = document.getElementById("itinerary-dest-badge");
  const tripSelect = document.getElementById("itinerary-trip-select");

  if (destElem) destElem.textContent = `${trip.destination} Itinerary Timeline`;
  if (badgeElem) badgeElem.textContent = trip.destination;
  if (datesElem) {
    datesElem.textContent = `${formatDateDisplay(trip.start_date)} – ${formatDateDisplay(trip.end_date)} (${trip.travellers} Travelers) • Budget: ${formatINR(trip.budget)}`;
  }

  if (tripSelect && tripSelect.value !== String(trip.trip_id)) {
    tripSelect.value = String(trip.trip_id);
  }

  if (typeof setActiveTrip === "function") {
    setActiveTrip(trip.trip_id, trip.destination, trip);
  }

  // Update trip subnavigation links
  document.querySelectorAll(".trip-subnav-link").forEach(link => {
    link.setAttribute("href", `${link.getAttribute("href").split("?")[0]}?id=${trip.trip_id}`);
  });

  // Apply destination-tailored modal inputs
  applyDestinationModalCustomization(trip);
}

function applyDestinationModalCustomization(trip) {
  const modalTitle = document.getElementById("itinerary-modal-title");
  if (modalTitle && !editingItemId) {
    modalTitle.textContent = `Add Activity to ${trip.destination} Schedule`;
  }

  const dateInput = document.getElementById("itinerary-date");
  if (dateInput) {
    if (!editingItemId) {
      dateInput.value = trip.start_date;
    }
    dateInput.min = trip.start_date;
    if (trip.end_date) {
      dateInput.max = trip.end_date;
    }
  }

  const actInput = document.getElementById("itinerary-activity");
  const locInput = document.getElementById("itinerary-location");
  const notesInput = document.getElementById("itinerary-notes");

  const destLower = (trip.destination || "").toLowerCase();

  if (destLower.includes("mysur") || destLower.includes("myso")) {
    if (actInput) actInput.placeholder = "e.g. Mysore Palace Visit, Chamundi Hill, Devaraja Market Walk";
    if (locInput) locInput.placeholder = "e.g. Mysore Palace, Chamundi Hills, Mysuru";
    if (notesInput) notesInput.placeholder = "e.g. Palace illumination at 7 PM, camera ticket included, dress code";
  } else if (destLower.includes("munnar")) {
    if (actInput) actInput.placeholder = "e.g. Tea Museum Tour, Eravikulam Trek, Mattupetty Dam";
    if (locInput) locInput.placeholder = "e.g. Tea Gardens, Munnar, Kerala";
    if (notesInput) notesInput.placeholder = "e.g. Warm jacket recommended, tickets booked online, camera gear";
  } else if (destLower.includes("goa")) {
    if (actInput) actInput.placeholder = "e.g. Scuba Diving, Fort Aguada, Sunset Dinner";
    if (locInput) locInput.placeholder = "e.g. North Goa, Baga Beach";
    if (notesInput) notesInput.placeholder = "e.g. Bring swimwear, tickets booked online";
  } else {
    if (actInput) actInput.placeholder = `e.g. Guided Sightseeing, Heritage Tour, Cultural Walk in ${trip.destination}`;
    if (locInput) locInput.placeholder = `e.g. Landmark, Venue, or Central ${trip.destination}`;
    if (notesInput) notesInput.placeholder = "e.g. Entry tickets, timings, dress code, tour guide contact...";
  }
}

async function loadQuickRecommendations(trip) {
  const container = document.getElementById("quick-recs-grid");
  const titleElem = document.getElementById("quick-recs-title");
  const subtitleElem = document.getElementById("quick-recs-subtitle");

  if (titleElem) titleElem.textContent = `Recommended Highlights for ${trip.destination}`;
  if (subtitleElem) {
    subtitleElem.textContent = `Curated experiences discovered from Experience Finder (:8001) ready to add to your ${trip.destination} schedule`;
  }

  if (!container) return;

  container.innerHTML = `
    <div style="grid-column: 1/-1; text-align: center; padding: 1.5rem; color: var(--text-muted);">
      <span class="spinner" style="border-top-color: var(--primary);"></span>
      <p style="margin-top: 0.5rem; font-size: 0.85rem;">Discovering places for ${escapeHtml(trip.destination)} from Experience Finder...</p>
    </div>
  `;

  try {
    const res = await ApiService.request(`/api/trips/${trip.trip_id}/recommendations`);
    const experiences = (res && res.experiences) ? res.experiences : [];

    if (experiences.length === 0) {
      container.innerHTML = `
        <div style="grid-column: 1/-1; padding: 1rem; color: var(--text-muted); font-size: 0.85rem; text-align: center;">
          No pre-cataloged experiences found for ${escapeHtml(trip.destination)}. You can use custom activities above or search other destinations in Recommendations.
        </div>
      `;
      return;
    }

    container.innerHTML = experiences.slice(0, 6).map(exp => {
      const priceText = (exp.price && exp.price > 0) ? formatINR(exp.price) : "Free";
      const expJson = JSON.stringify({
        activity: exp.name,
        category: exp.category || "Sightseeing",
        estimated_cost: exp.price || 0,
        location: exp.locality ? `${exp.locality}, ${exp.destination}` : (exp.destination || trip.destination),
        notes: `Discovered from Experience Finder (${exp.category || 'Sightseeing'})`
      }).replace(/"/g, '&quot;');

      return `
        <div class="card" style="padding: 1rem; border: 1px solid var(--border-color); display: flex; flex-direction: column; justify-content: space-between; gap: 0.75rem; background: var(--bg-card);">
          <div>
            <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 0.5rem; margin-bottom: 0.35rem;">
              <span class="badge" style="background: rgba(37,99,235,0.1); color: var(--primary); font-size: 0.72rem; padding: 0.2rem 0.45rem;">
                ${escapeHtml(exp.category || 'Highlight')}
              </span>
              <strong style="color: var(--success); font-size: 0.85rem;">${priceText}</strong>
            </div>
            <h4 style="font-size: 0.95rem; margin: 0 0 0.35rem 0; color: var(--text-main); line-height: 1.3;">
              ${escapeHtml(exp.name)}
            </h4>
            <div style="font-size: 0.78rem; color: var(--text-muted);">
              📍 ${escapeHtml(exp.locality ? `${exp.locality}, ${exp.destination}` : (exp.destination || trip.destination))}
            </div>
          </div>
          <div style="display: flex; gap: 0.5rem;">
            <button 
              type="button" 
              class="btn btn-primary btn-sm" 
              style="flex: 1; font-size: 0.78rem; padding: 0.4rem;"
              onclick="handleQuickAddExperience(${expJson})">
              + Quick Add
            </button>
            <button 
              type="button" 
              class="btn btn-outline btn-sm" 
              style="font-size: 0.78rem; padding: 0.4rem;"
              title="Customize date & time before adding"
              onclick="handleCustomizeAndAddExperience(${expJson})">
              ✏ Custom
            </button>
          </div>
        </div>
      `;
    }).join("");
  } catch (err) {
    container.innerHTML = `
      <div style="grid-column: 1/-1; padding: 1rem; color: var(--text-muted); font-size: 0.85rem; text-align: center;">
        Explore tailored highlights anytime in the <a href="recommendations.html?id=${trip.trip_id}">Recommendations Module &rarr;</a>
      </div>
    `;
  }
}

async function handleQuickAddExperience(expData) {
  if (!currentTripObj) return;

  const itemData = {
    activity: expData.activity,
    date: currentTripObj.start_date,
    time: "10:00",
    location: expData.location || currentTripObj.destination,
    category: expData.category || "Sightseeing",
    estimated_cost: parseFloat(expData.estimated_cost) || 0.0,
    notes: expData.notes || `Scheduled for ${currentTripObj.destination}`
  };

  try {
    await ApiService.itinerary.add(currentTripObj.trip_id, itemData);
    showToast(`Added "${expData.activity}" to Day 1 schedule!`, "success");
    await loadItineraryData();
  } catch (err) {
    showToast(err.message || "Failed to add activity", "error");
  }
}

function handleCustomizeAndAddExperience(expData) {
  resetItineraryModalToAddMode();

  const activityInput = document.getElementById("itinerary-activity");
  const locationInput = document.getElementById("itinerary-location");
  const costInput = document.getElementById("itinerary-cost");
  const categoryInput = document.getElementById("itinerary-category");
  const notesInput = document.getElementById("itinerary-notes");

  if (activityInput) activityInput.value = expData.activity || "";
  if (locationInput) locationInput.value = expData.location || "";
  if (costInput) costInput.value = expData.estimated_cost || 0;
  if (notesInput) notesInput.value = expData.notes || "";

  if (categoryInput && expData.category) {
    // Attempt match
    const opts = Array.from(categoryInput.options).map(o => o.value.toLowerCase());
    const match = opts.find(o => o.includes(expData.category.toLowerCase()));
    if (match) {
      categoryInput.value = categoryInput.options[opts.indexOf(match)].value;
    }
  }

  openModal("add-itinerary-modal");
}

function renderItineraryList(items) {
  const container = document.getElementById("itinerary-list-container");
  const emptyState = document.getElementById("itinerary-empty-state");
  if (!container) return;

  if (!items || items.length === 0) {
    container.innerHTML = "";
    if (emptyState) emptyState.style.display = "flex";
    return;
  }

  if (emptyState) emptyState.style.display = "none";

  // Group by Date
  const grouped = {};
  items.forEach(item => {
    if (!grouped[item.date]) grouped[item.date] = [];
    grouped[item.date].push(item);
  });

  const dates = Object.keys(grouped).sort();

  container.innerHTML = dates.map((dateStr, dayIndex) => {
    const dayItems = grouped[dateStr];
    return `
      <div class="itinerary-day-group">
        <div class="itinerary-day-header">
          <div class="itinerary-day-title">
            <span class="day-badge">Day ${dayIndex + 1}</span>
            <span>${formatDateDisplay(dateStr)}</span>
          </div>
          <span style="font-size: 0.85rem; color: var(--text-muted);">
            ${dayItems.length} ${dayItems.length === 1 ? 'activity' : 'activities'}
          </span>
        </div>

        <div class="itinerary-timeline">
          ${dayItems.map(item => `
            <div class="itinerary-item">
              <div class="itinerary-time">${item.time}</div>
              <div class="itinerary-dot"></div>
              <div class="itinerary-card">
                <div class="itinerary-details">
                  <div class="itinerary-activity-name">${escapeHtml(item.activity)}</div>
                  <div class="itinerary-meta" style="display: flex; flex-wrap: wrap; gap: 0.75rem; align-items: center; margin-top: 0.35rem;">
                    <span>📍 ${escapeHtml(item.location || (currentTripObj ? currentTripObj.destination : 'Location TBA'))}</span>
                    <span class="badge" style="background: rgba(37,99,235,0.1); color: var(--primary); font-size: 0.75rem; padding: 0.2rem 0.5rem; border-radius: 4px;">
                      🏷 ${escapeHtml(item.category || 'General')}
                    </span>
                    <span>💰 ${item.estimated_cost > 0 ? formatINR(item.estimated_cost) : 'Free'}</span>
                  </div>
                  ${item.notes ? `<div class="itinerary-notes">📝 ${escapeHtml(item.notes)}</div>` : ''}
                </div>
                <div class="itinerary-actions" style="display: flex; gap: 0.35rem; align-items: center;">
                  <button class="btn btn-ghost btn-sm" title="Edit Activity" onclick="handleEditItineraryItem(${item.item_id})">
                    ✏
                  </button>
                  <button class="btn btn-ghost btn-sm text-danger" title="Delete Activity" onclick="handleDeleteItineraryItem(${item.item_id})">
                    ✕
                  </button>
                </div>
              </div>
            </div>
          `).join("")}
        </div>
      </div>
    `;
  }).join("");
}

function handleEditItineraryItem(itemId) {
  const item = cachedItineraryItems.find(i => i.item_id === itemId);
  if (!item) return;

  editingItemId = itemId;
  const title = document.getElementById("itinerary-modal-title");
  if (title) title.textContent = "Edit Scheduled Activity";

  const activityInput = document.getElementById("itinerary-activity");
  const dateInput = document.getElementById("itinerary-date");
  const timeInput = document.getElementById("itinerary-time");
  const locationInput = document.getElementById("itinerary-location");
  const categoryInput = document.getElementById("itinerary-category");
  const costInput = document.getElementById("itinerary-cost");
  const notesInput = document.getElementById("itinerary-notes");

  if (activityInput) activityInput.value = item.activity || "";
  if (dateInput) {
    dateInput.value = item.date || "";
    if (currentTripObj) {
      dateInput.min = currentTripObj.start_date;
      if (currentTripObj.end_date) dateInput.max = currentTripObj.end_date;
    }
  }
  if (timeInput) timeInput.value = item.time || "";
  if (locationInput) locationInput.value = item.location || "";
  if (categoryInput) categoryInput.value = item.category || "General";
  if (costInput) costInput.value = item.estimated_cost || 0;
  if (notesInput) notesInput.value = item.notes || "";

  const form = document.getElementById("add-itinerary-form");
  if (form) {
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) submitBtn.textContent = "Save Changes";
  }

  openModal("add-itinerary-modal");
}

function setupAddItineraryModal() {
  const form = document.getElementById("add-itinerary-form");
  if (!form) return;

  const activityInput = document.getElementById("itinerary-activity");
  const dateInput = document.getElementById("itinerary-date");
  const timeInput = document.getElementById("itinerary-time");
  const locationInput = document.getElementById("itinerary-location");
  const categoryInput = document.getElementById("itinerary-category");
  const costInput = document.getElementById("itinerary-cost");
  const notesInput = document.getElementById("itinerary-notes");

  [activityInput, dateInput, timeInput].forEach(inp => {
    if (inp) inp.addEventListener("input", () => Validator.clearFieldError(inp));
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    let isValid = true;

    if (!activityInput.value.trim()) {
      Validator.setFieldError(activityInput, "Activity name is required");
      isValid = false;
    }
    if (!dateInput.value) {
      Validator.setFieldError(dateInput, "Date is required");
      isValid = false;
    }
    if (!timeInput.value) {
      Validator.setFieldError(timeInput, "Time is required");
      isValid = false;
    }

    if (!isValid) return;

    const itemData = {
      activity: activityInput.value.trim(),
      date: dateInput.value,
      time: timeInput.value,
      location: locationInput && locationInput.value.trim() ? locationInput.value.trim() : (currentTripObj ? currentTripObj.destination : ""),
      category: categoryInput ? categoryInput.value : "General",
      estimated_cost: costInput && costInput.value ? parseFloat(costInput.value) : 0.0,
      notes: notesInput ? notesInput.value.trim() : ""
    };

    const submitBtn = form.querySelector('button[type="submit"]');
    submitBtn.disabled = true;

    try {
      if (editingItemId) {
        await ApiService.itinerary.update(editingItemId, itemData);
        showToast("Activity updated successfully!", "success");
        editingItemId = null;
      } else {
        await ApiService.itinerary.add(currentTripId, itemData);
        showToast(`Activity added to ${currentTripObj ? currentTripObj.destination : 'your'} itinerary!`, "success");
      }
      closeModal("add-itinerary-modal");
      form.reset();
      await loadItineraryData();
    } catch (err) {
      showToast(err.message || "Failed to save activity", "error");
    } finally {
      submitBtn.disabled = false;
    }
  });
}

async function handleDeleteItineraryItem(itemId) {
  if (confirm("Remove this activity from your itinerary?")) {
    try {
      await ApiService.itinerary.delete(itemId);
      showToast("Activity removed", "warning");
      await loadItineraryData();
    } catch (err) {
      showToast(err.message || "Failed to delete activity", "error");
    }
  }
}
