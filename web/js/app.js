const STORAGE_KEY = "erojuentiii_user_id";

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
    throw new Error(data.detail || `Request failed (${response.status})`);
  }
  return data;
}

function selectedMealType() {
  return document.querySelector(".meal-type.active")?.dataset.mealType || "lunch";
}

function renderMeal(meal) {
  const macros = meal.macros_estimate || {};
  const macroParts = [
    macros.calories != null ? `${macros.calories} cal` : null,
    macros.protein_g != null ? `${macros.protein_g}g protein` : null,
  ].filter(Boolean);

  const ingredients = (meal.ingredients || []).map((item) => `<li>${item}</li>`).join("");
  const steps = (meal.steps || []).map((step, index) => `<li>${step}</li>`).join("");

  document.getElementById("meal-output").innerHTML = `
    <h3>${meal.name}</h3>
    <p>${meal.description || ""}</p>
    ${macroParts.length ? `<p><strong>Macros:</strong> ${macroParts.join(" · ")}</p>` : ""}
    ${meal.time_minutes ? `<p><strong>Time:</strong> ~${meal.time_minutes} min</p>` : ""}
    ${ingredients ? `<p><strong>Ingredients</strong></p><ul>${ingredients}</ul>` : ""}
    ${steps ? `<p><strong>Steps</strong></p><ol>${steps}</ol>` : ""}
  `;
  document.getElementById("result").classList.remove("hidden");
}

function renderHistory(items) {
  const list = document.getElementById("history");
  if (!items.length) {
    list.innerHTML = "<li>No meals yet.</li>";
    return;
  }
  list.innerHTML = items
    .map((item) => {
      const name = item.meal?.name || "Meal";
      const when = item.created_at ? new Date(item.created_at).toLocaleString() : "";
      return `<li><strong>${name}</strong>${when ? ` — ${when}` : ""}</li>`;
    })
    .join("");
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
  const meals = await apiRequest(`/api/user/meals?user_id=${encodeURIComponent(userId)}&limit=5`);
  renderHistory(meals);
}

async function savePantry() {
  const userId = getUserId();
  const pantry = parsePantry(document.getElementById("pantry").value);
  await apiRequest(`/api/user/pantry?user_id=${encodeURIComponent(userId)}`, {
    method: "PUT",
    body: JSON.stringify({ pantry }),
  });
  setStatus("Pantry saved.");
}

async function savePrefs() {
  const userId = getUserId();
  await apiRequest(`/api/user/prefs?user_id=${encodeURIComponent(userId)}`, {
    method: "PUT",
    body: JSON.stringify({
      cuisine: document.getElementById("cuisine").value.trim() || null,
      region: document.getElementById("region").value.trim() || null,
    }),
  });
  setStatus("Preferences saved.");
}

async function getMeal() {
  const userId = getUserId();
  setStatus("Finding a meal...");
  const meal = await apiRequest("/api/get-meal", {
    method: "POST",
    body: JSON.stringify({
      meal_type: selectedMealType(),
      user_id: userId,
      custom: document.getElementById("custom").value.trim() || null,
    }),
  });
  renderMeal(meal);
  setStatus("Meal ready.");
  await loadHistory();
}

document.querySelectorAll(".meal-type").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".meal-type").forEach((el) => el.classList.remove("active"));
    button.classList.add("active");
  });
});

document.getElementById("save-pantry").addEventListener("click", () =>
  savePantry().catch((err) => setStatus(err.message, true))
);
document.getElementById("save-prefs").addEventListener("click", () =>
  savePrefs().catch((err) => setStatus(err.message, true))
);
document.getElementById("get-meal").addEventListener("click", () =>
  getMeal().catch((err) => setStatus(err.message, true))
);

loadProfile()
  .then(loadHistory)
  .catch((err) => setStatus(err.message, true));
