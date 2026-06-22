const STORAGE_KEY = "erojuentiii_user_id";

let pendingSuggestion = null;
let rejectedMeals = [];
let historyMeals = [];

function apiBase() {
  return window.APP_CONFIG?.API_BASE || "http://localhost:8000";
}

function getUserId() {
  let userId = localStorage.getItem(STORAGE_KEY);
  if (!userId) {
    userId = crypto.randomUUID();
    localStorage.setItem(STORAGE_KEY, userId);
  }
  return userId;
}

function setStatus(message, isError = false) {
  const el = document.getElementById("status");
  el.textContent = message;
  el.className = isError ? "status error" : "status";
}

function parsePantry(raw) {
  return raw
    .split(/[,;\n]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

async function apiRequest(path, options = {}) {
  const response = await fetch(`${apiBase()}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = Array.isArray(data.detail)
      ? data.detail.map((item) => item.msg || JSON.stringify(item)).join(", ")
      : data.detail;
    throw new Error(detail || `Request failed (${response.status})`);
  }
  return data;
}

function selectedMealType() {
  return document.querySelector(".meal-type.active")?.dataset.mealType || "lunch";
}

function setSuggestionActionsEnabled(enabled) {
  document.getElementById("approve-meal").disabled = !enabled;
  document.getElementById("retry-meal").disabled = !enabled;
}

function setSuggestButtonLoading(loading) {
  document.getElementById("get-meal").disabled = loading;
}

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function formatMacroLine(macros) {
  if (!macros) {
    return "";
  }
  const parts = [
    macros.calories != null ? `${macros.calories} cal` : null,
    macros.protein_g != null ? `${macros.protein_g}g protein` : null,
    macros.carbs_g != null ? `${macros.carbs_g}g carbs` : null,
    macros.fat_g != null ? `${macros.fat_g}g fat` : null,
  ].filter(Boolean);
  return parts.join(" · ");
}

function buildComponentHtml(component) {
  const role = component.role ? String(component.role) : "side";
  const ingredients = (component.ingredients || [])
    .map((item) => `<li>${escapeHtml(item)}</li>`)
    .join("");
  const steps = (component.steps || [])
    .map((step) => `<li>${escapeHtml(step)}</li>`)
    .join("");
  const macroLine = formatMacroLine(component.macros_estimate);

  let html = `
    <article class="meal-component">
      <div class="component-header">
        <span class="component-role">${escapeHtml(role)}</span>
        <h4>${escapeHtml(component.name || "Component")}</h4>
      </div>
  `;
  if (macroLine) {
    html += `<p class="component-macros">${escapeHtml(macroLine)}</p>`;
  }
  if (ingredients) {
    html += `<h5>Ingredients</h5><ul>${ingredients}</ul>`;
  }
  if (steps) {
    html += `<h5>Steps</h5><ol>${steps}</ol>`;
  }
  html += "</article>";
  return html;
}

function buildMealDetailsHtml(meal) {
  const macroLine = formatMacroLine(meal.macros_estimate);

  let html = "";
  if (macroLine) {
    html += `<div class="modal-section"><h3>Plate macros</h3><p>${escapeHtml(macroLine)}</p></div>`;
  }
  if (meal.time_minutes) {
    html += `<div class="modal-section"><h3>Time</h3><p>~${escapeHtml(meal.time_minutes)} min</p></div>`;
  }
  if (meal.uses_pantry?.length) {
    html += `<div class="modal-section"><h3>From pantry</h3><p>${escapeHtml(meal.uses_pantry.join(", "))}</p></div>`;
  }

  const components = meal.components || [];
  if (components.length) {
    html += `<div class="modal-section"><h3>Components</h3>${components.map(buildComponentHtml).join("")}</div>`;
    return html;
  }

  const ingredients = (meal.ingredients || [])
    .map((item) => `<li>${escapeHtml(item)}</li>`)
    .join("");
  const steps = (meal.steps || [])
    .map((step) => `<li>${escapeHtml(step)}</li>`)
    .join("");
  if (ingredients) {
    html += `<div class="modal-section"><h3>Ingredients</h3><ul>${ingredients}</ul></div>`;
  }
  if (steps) {
    html += `<div class="modal-section"><h3>Steps</h3><ol>${steps}</ol></div>`;
  }
  return html || "<p>No extra details.</p>";
}

function openMealModal(meal) {
  document.getElementById("meal-modal-title").textContent = meal.name || "Meal";
  document.getElementById("meal-modal-description").textContent = meal.description || "";
  document.getElementById("meal-modal-body").innerHTML = buildMealDetailsHtml(meal);
  document.getElementById("meal-modal").classList.remove("hidden");
}

function closeMealModal() {
  document.getElementById("meal-modal").classList.add("hidden");
}

function openSettingsModal() {
  document.getElementById("settings-modal").classList.remove("hidden");
}

function closeSettingsModal() {
  document.getElementById("settings-modal").classList.add("hidden");
}

function closeTopModal() {
  if (!document.getElementById("meal-modal").classList.contains("hidden")) {
    closeMealModal();
    return;
  }
  if (!document.getElementById("settings-modal").classList.contains("hidden")) {
    closeSettingsModal();
  }
}

function renderMeal(meal) {
  document.getElementById("meal-output").innerHTML = `
    <div class="meal-summary">
      <h3>${escapeHtml(meal.name)}</h3>
      <p>${escapeHtml(meal.description || "")}</p>
      <button type="button" class="link-button" id="view-meal-details">View recipe & details</button>
    </div>
  `;
  document.getElementById("view-meal-details").addEventListener("click", () => openMealModal(meal));
  document.getElementById("result").classList.remove("hidden");
  setSuggestionActionsEnabled(true);
}

function renderHistory(items) {
  historyMeals = items;
  const list = document.getElementById("history");
  if (!items.length) {
    list.innerHTML = "<li>No approved meals yet.</li>";
    return;
  }
  list.innerHTML = items
    .map((item, index) => {
      const name = item.meal?.name || "Meal";
      const when = item.created_at ? new Date(item.created_at).toLocaleString() : "";
      return `<li data-history-index="${index}"><strong>${escapeHtml(name)}</strong>${
        when ? `<span class="meal-date">${escapeHtml(when)}</span>` : ""
      }</li>`;
    })
    .join("");

  list.querySelectorAll("li[data-history-index]").forEach((el) => {
    el.addEventListener("click", () => {
      const item = historyMeals[Number(el.dataset.historyIndex)];
      if (item?.meal) {
        openMealModal(item.meal);
      }
    });
  });
}

async function loadProfile() {
  const userId = getUserId();
  const profile = await apiRequest(`/api/user?user_id=${encodeURIComponent(userId)}`);
  document.getElementById("pantry").value = (profile.pantry || []).join(", ");
  document.getElementById("cuisine").value = profile.prefs?.cuisine || "";
  document.getElementById("region").value = profile.prefs?.region || "";
  setStatus("Ready.");
}

async function loadHistory() {
  const userId = getUserId();
  const meals = await apiRequest(`/api/user/meals?user_id=${encodeURIComponent(userId)}&limit=20`);
  renderHistory(meals);
}

async function saveSettings() {
  const userId = getUserId();
  const pantry = parsePantry(document.getElementById("pantry").value);
  await apiRequest(`/api/user/pantry?user_id=${encodeURIComponent(userId)}`, {
    method: "PUT",
    body: JSON.stringify({ pantry }),
  });
  await apiRequest(`/api/user/prefs?user_id=${encodeURIComponent(userId)}`, {
    method: "PUT",
    body: JSON.stringify({
      cuisine: document.getElementById("cuisine").value.trim() || null,
      region: document.getElementById("region").value.trim() || null,
    }),
  });
  setStatus("Settings saved.");
  closeSettingsModal();
}

function buildMealRequest() {
  return {
    meal_type: selectedMealType(),
    user_id: getUserId(),
    custom: document.getElementById("custom").value.trim() || null,
    rejected_meals: rejectedMeals,
  };
}

async function getMeal() {
  setStatus("Finding a meal...");
  setSuggestionActionsEnabled(false);
  setSuggestButtonLoading(true);
  try {
    const suggestion = await apiRequest("/api/get-meal", {
      method: "POST",
      body: JSON.stringify(buildMealRequest()),
    });
    pendingSuggestion = suggestion;
    renderMeal(suggestion.meal);
    setStatus("Like it? Save it — or try another.");
  } finally {
    setSuggestButtonLoading(false);
  }
}

async function approveMeal() {
  if (!pendingSuggestion) {
    return;
  }
  setStatus("Saving meal...");
  setSuggestionActionsEnabled(false);
  await apiRequest("/api/meals/approve", {
    method: "POST",
    body: JSON.stringify({
      user_id: getUserId(),
      params: pendingSuggestion.params,
      meal: pendingSuggestion.meal,
    }),
  });
  pendingSuggestion = null;
  rejectedMeals = [];
  setSuggestionActionsEnabled(false);
  setStatus("Meal saved.");
  await loadHistory();
}

async function retryMeal() {
  if (!pendingSuggestion?.meal?.name) {
    await getMeal();
    return;
  }
  rejectedMeals.push(pendingSuggestion.meal.name);
  pendingSuggestion = null;
  await getMeal();
}

document.querySelectorAll(".meal-type").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".meal-type").forEach((el) => el.classList.remove("active"));
    button.classList.add("active");
  });
});

document.querySelectorAll("[data-close-meal]").forEach((el) => {
  el.addEventListener("click", closeMealModal);
});

document.querySelectorAll("[data-close-settings]").forEach((el) => {
  el.addEventListener("click", closeSettingsModal);
});

document.getElementById("open-settings").addEventListener("click", openSettingsModal);

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closeTopModal();
  }
});

document.getElementById("save-settings").addEventListener("click", () =>
  saveSettings().catch((err) => setStatus(err.message, true))
);
document.getElementById("get-meal").addEventListener("click", () => {
  rejectedMeals = [];
  getMeal().catch((err) => setStatus(err.message, true));
});
document.getElementById("approve-meal").addEventListener("click", () =>
  approveMeal().catch((err) => setStatus(err.message, true))
);
document.getElementById("retry-meal").addEventListener("click", () =>
  retryMeal().catch((err) => setStatus(err.message, true))
);

setSuggestionActionsEnabled(false);
loadProfile()
  .then(loadHistory)
  .catch((err) => setStatus(err.message, true));
