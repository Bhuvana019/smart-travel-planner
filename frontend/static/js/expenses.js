/**
 * ============================================================================
 * SMART TRAVEL PLANNER - EXPENSES & BUDGET CONTROLLER
 * Real FastAPI Backend Data Binding & Automatic Budget Metrics with Full CRUD
 * ============================================================================
 */

let currentTripId = 130;
let cachedExpenseData = null;
let editingExpenseId = null;

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
  initExpensesPage();
});

async function initExpensesPage() {
  const urlParams = new URLSearchParams(window.location.search);
  const tripParam = urlParams.get("id");
  if (tripParam && !isNaN(parseInt(tripParam, 10)) && parseInt(tripParam, 10) !== 101) {
    currentTripId = parseInt(tripParam, 10);
  } else if (typeof getActiveTripId === "function" && getActiveTripId() && getActiveTripId() !== 101) {
    currentTripId = getActiveTripId();
  } else {
    // If no valid ID param provided, fetch current user's first trip
    try {
      const trips = await ApiService.trips.list();
      if (trips && trips.length > 0) {
        const activeStoredId = localStorage.getItem("active_trip_id");
        const match = trips.find(t => String(t.trip_id) === String(activeStoredId)) || trips.find(t => (t.destination || '').toLowerCase().includes("mysur")) || trips[trips.length - 1];
        currentTripId = match.trip_id;
        if (typeof setActiveTrip === "function") {
          setActiveTrip(match.trip_id, match.destination, match);
        }
      } else {
        currentTripId = 130;
      }
    } catch (e) {
      currentTripId = 130;
    }
  }

  setupAddExpenseModal();
  setupExpenseCategoryFilter();
  setupAddExpenseButtons();
  await loadExpensesData();
}

function setupAddExpenseButtons() {
  document.querySelectorAll('[onclick*="add-expense-modal"]').forEach(btn => {
    btn.addEventListener("click", () => {
      resetExpenseModalToAddMode();
    });
  });
}

function resetExpenseModalToAddMode() {
  editingExpenseId = null;
  const title = document.getElementById("expense-modal-title");
  if (title) title.textContent = "Log New Expense";

  const form = document.getElementById("add-expense-form");
  if (form) {
    form.reset();
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) submitBtn.textContent = "+ Log Expense";
  }

  const dateInput = document.getElementById("expense-date");
  if (dateInput) {
    dateInput.value = new Date().toISOString().split("T")[0];
  }

  const notesInput = document.getElementById("expense-notes");
  if (notesInput) {
    notesInput.value = "";
  }
}

async function loadExpensesData(categoryFilter = "All") {
  try {
    let url = `/api/trips/${currentTripId}/expenses`;
    if (categoryFilter && categoryFilter !== "All") {
      url += `?category=${encodeURIComponent(categoryFilter)}`;
    }
    cachedExpenseData = await ApiService.request(url);
    renderExpensesView(cachedExpenseData, categoryFilter);
  } catch (err) {
    console.warn("Failed to fetch expenses for trip ID", currentTripId, err);
    if (typeof ApiService !== "undefined" && ApiService.trips) {
      try {
        const trips = await ApiService.trips.list();
        if (trips && trips.length > 0) {
          const fallbackTrip = trips.find(t => t.trip_id === currentTripId) || trips[0];
          currentTripId = fallbackTrip.trip_id;
          let url = `/api/trips/${currentTripId}/expenses`;
          if (categoryFilter && categoryFilter !== "All") {
            url += `?category=${encodeURIComponent(categoryFilter)}`;
          }
          cachedExpenseData = await ApiService.request(url);
          renderExpensesView(cachedExpenseData, categoryFilter);
          return;
        }
      } catch (e2) {}
    }
  }
}

function renderExpensesView(data, categoryFilter = "All") {
  const destElem = document.getElementById("expenses-dest-title");
  const datesElem = document.getElementById("expenses-dates-sub");
  if (destElem) destElem.textContent = `${data.destination} Expenses & Budget`;
  if (datesElem) datesElem.textContent = `Target Budget: ${formatINR(data.budget)}`;

  if (typeof setActiveTrip === "function") {
    setActiveTrip(data.trip_id || currentTripId, data.destination, data);
  }

  // Update trip subnavigation links
  document.querySelectorAll(".trip-subnav-link").forEach(link => {
    link.setAttribute("href", `${link.getAttribute("href").split("?")[0]}?id=${data.trip_id || currentTripId}`);
  });

  // Render Metric Cards
  const budgetValElem = document.getElementById("metric-budget-val");
  const spentValElem = document.getElementById("metric-spent-val");
  const remainingValElem = document.getElementById("metric-remaining-val");
  const percentTextElem = document.getElementById("budget-percent-text");
  const progressBarFill = document.getElementById("budget-progress-fill");

  if (budgetValElem) budgetValElem.textContent = formatINR(data.budget);
  if (spentValElem) spentValElem.textContent = formatINR(data.total_spent);
  if (remainingValElem) remainingValElem.textContent = formatINR(data.remaining_budget);

  const pct = data.budget_used_percentage || 0;
  if (percentTextElem) {
    percentTextElem.innerHTML = data.budget_exceeded 
      ? `<span style="color: var(--danger); font-weight: bold;">⚠ Budget Exceeded (${pct}%)</span>`
      : `${pct}% of budget spent`;
  }

  if (progressBarFill) {
    progressBarFill.style.width = `${Math.min(100, pct)}%`;
    progressBarFill.className = `progress-bar-fill ${data.budget_exceeded ? 'fill-danger' : pct > 70 ? 'fill-warn' : 'fill-safe'}`;
  }

  // Budget Warning Banner
  const warningBanner = document.getElementById("budget-warning-banner");
  if (warningBanner) {
    if (data.budget_exceeded) {
      warningBanner.style.display = "block";
      const overspent = Math.abs(data.remaining_budget);
      warningBanner.innerHTML = `⚠️ <strong>Budget Exceeded!</strong> Total expenses have exceeded your planned trip budget by ${formatINR(overspent)} (${pct}% spent). You can still continue logging expenses.`;
    } else {
      warningBanner.style.display = "none";
    }
  }

  // Render Category Breakdown Bars
  renderCategoryBreakdown(data.category_breakdown || {}, data.total_spent);

  // Table items (already category-filtered if from backend, or double-check client side)
  let expenses = data.expenses || [];
  if (categoryFilter && categoryFilter !== "All") {
    expenses = expenses.filter(e => e.category.toLowerCase() === categoryFilter.toLowerCase());
  }

  renderExpensesTable(expenses);
}

function renderCategoryBreakdown(categoryTotals, totalSpent) {
  const container = document.getElementById("category-breakdown-container");
  if (!container) return;

  const categories = Object.keys(categoryTotals);
  container.innerHTML = categories.map(cat => {
    const amount = categoryTotals[cat];
    const pct = totalSpent > 0 ? Math.round((amount / totalSpent) * 100) : 0;
    return `
      <div class="category-row">
        <div class="category-row-head">
          <span class="category-tag ${cat.toLowerCase()}">${cat}</span>
          <span style="color: var(--text-main); font-weight: 700;">
            ${formatINR(amount)} <span style="font-size: 0.75rem; color: var(--text-muted); font-weight: normal;">(${pct}%)</span>
          </span>
        </div>
        <div class="progress-bar-track" style="height: 6px;">
          <div class="progress-bar-fill" style="width: ${pct}%; background: var(--primary);"></div>
        </div>
      </div>
    `;
  }).join("");
}

function renderExpensesTable(expenses) {
  const tbody = document.getElementById("expenses-table-body");
  const emptyState = document.getElementById("expenses-empty-state");
  if (!tbody) return;

  if (expenses.length === 0) {
    tbody.innerHTML = "";
    if (emptyState) emptyState.style.display = "flex";
    return;
  }

  if (emptyState) emptyState.style.display = "none";

  tbody.innerHTML = expenses.map(item => `
    <tr>
      <td>${formatDateDisplay(item.expense_date)}</td>
      <td>
        <span class="category-tag ${(item.category || '').toLowerCase()}">
          ${escapeHtml(item.category)}
        </span>
      </td>
      <td style="font-weight: 600; color: var(--text-main);">
        ${escapeHtml(item.description || item.title || "")}
      </td>
      <td style="font-weight: 700; color: var(--text-main);">
        ${formatINR(item.amount)}
      </td>
      <td style="color: var(--text-muted); font-size: 0.875rem;">
        ${escapeHtml(item.notes || '-')}
      </td>
      <td style="text-align: right; white-space: nowrap;">
        <button class="btn btn-ghost btn-sm" title="Edit expense" onclick="handleEditExpense(${item.expense_id})">
          ✏
        </button>
        <button class="btn btn-ghost btn-sm text-danger" title="Delete expense" onclick="handleDeleteExpense(${item.expense_id})">
          ✕
        </button>
      </td>
    </tr>
  `).join("");
}

function handleEditExpense(expenseId) {
  if (!cachedExpenseData || !cachedExpenseData.expenses) return;
  const item = cachedExpenseData.expenses.find(e => e.expense_id === expenseId);
  if (!item) return;

  editingExpenseId = expenseId;
  const title = document.getElementById("expense-modal-title");
  if (title) title.textContent = "Edit Expense Transaction";

  const catInput = document.getElementById("expense-category");
  const amountInput = document.getElementById("expense-amount");
  const dateInput = document.getElementById("expense-date");
  const descInput = document.getElementById("expense-description");
  const notesInput = document.getElementById("expense-notes");

  if (catInput) catInput.value = item.category || "Food";
  if (amountInput) amountInput.value = item.amount || "";
  if (dateInput) dateInput.value = item.expense_date || "";
  if (descInput) descInput.value = item.description || item.title || "";
  if (notesInput) notesInput.value = item.notes || "";

  const form = document.getElementById("add-expense-form");
  if (form) {
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) submitBtn.textContent = "Save Changes";
  }

  openModal("add-expense-modal");
}

function setupAddExpenseModal() {
  const form = document.getElementById("add-expense-form");
  if (!form) return;

  const catInput = document.getElementById("expense-category");
  const amountInput = document.getElementById("expense-amount");
  const dateInput = document.getElementById("expense-date");
  const descInput = document.getElementById("expense-description");
  const notesInput = document.getElementById("expense-notes");

  [catInput, amountInput, dateInput].forEach(inp => {
    if (inp) inp.addEventListener("input", () => Validator.clearFieldError(inp));
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    let isValid = true;

    if (!catInput.value) {
      Validator.setFieldError(catInput, "Category is required");
      isValid = false;
    }

    const amount = parseFloat(amountInput.value);
    if (isNaN(amount) || amount <= 0) {
      Validator.setFieldError(amountInput, "Amount must be greater than ₹0");
      isValid = false;
    }

    if (!dateInput.value) {
      Validator.setFieldError(dateInput, "Date is required");
      isValid = false;
    }

    if (!isValid) return;

    const expenseData = {
      category: catInput.value,
      amount: amount,
      description: descInput && descInput.value.trim() ? descInput.value.trim() : "General Expense",
      title: descInput && descInput.value.trim() ? descInput.value.trim() : "General Expense",
      expense_date: dateInput.value,
      notes: notesInput && notesInput.value.trim() ? notesInput.value.trim() : ""
    };

    const submitBtn = form.querySelector('button[type="submit"]');
    submitBtn.disabled = true;

    try {
      if (editingExpenseId) {
        await ApiService.expenses.update(editingExpenseId, expenseData);
        showToast(`Expense updated! Budget recalculations refreshed.`, "success");
        editingExpenseId = null;
      } else {
        await ApiService.expenses.add(currentTripId, expenseData);
        showToast(`Logged ${formatINR(amount)} to ${catInput.value}!`, "success");
      }
      closeModal("add-expense-modal");
      form.reset();
      resetExpenseModalToAddMode();
      await loadExpensesData();
    } catch (err) {
      showToast(err.message || "Failed to log expense", "error");
    } finally {
      submitBtn.disabled = false;
    }
  });
}

function setupExpenseCategoryFilter() {
  const select = document.getElementById("expense-filter-select");
  if (select) {
    select.addEventListener("change", (e) => {
      loadExpensesData(e.target.value);
    });
  }
}

async function handleDeleteExpense(expenseId) {
  if (confirm("Delete this expense item? Budget totals will automatically update.")) {
    try {
      await ApiService.expenses.delete(expenseId);
      showToast("Expense removed and budget updated", "warning");
      await loadExpensesData();
    } catch (err) {
      showToast(err.message || "Failed to delete expense", "error");
    }
  }
}
