const uploadSection = document.getElementById("uploadSection");
const loadingSection = document.getElementById("loadingSection");
const errorSection = document.getElementById("errorSection");
const resultsSection = document.getElementById("resultsSection");
const settingsSection = document.getElementById("settingsSection");
const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("fileInput");
const browseBtn = document.getElementById("browseBtn");
const retryBtn = document.getElementById("retryBtn");
const newEvalBtn = document.getElementById("newEvalBtn");
const settingsToggle = document.getElementById("settingsToggle");
const providerSelect = document.getElementById("providerSelect");
const modelSelect = document.getElementById("modelSelect");
const modelField = document.getElementById("modelField");
const geminiModelField = document.getElementById("geminiModelField");
const geminiModelSelect = document.getElementById("geminiModelSelect");
const geminiKeyGroup = document.getElementById("geminiKeyGroup");
const geminiApiKey = document.getElementById("geminiApiKey");
const geminiKeyPreview = document.getElementById("geminiKeyPreview");
const saveSettingsBtn = document.getElementById("saveSettingsBtn");
const refreshModelsBtn = document.getElementById("refreshModelsBtn");
const settingsStatus = document.getElementById("settingsStatus");
let savedGeminiKeyValid = false;

function show(section) {
  [uploadSection, loadingSection, errorSection, resultsSection].forEach((el) => {
    el.classList.toggle("hidden", el !== section);
  });
}

function reset() {
  fileInput.value = "";
  show(uploadSection);
}

const GEMINI_DEFAULT_MODEL = "gemini-2.5-flash-lite";

function isGeminiModel(name) {
  return (name || "").trim().toLowerCase().startsWith("gemini");
}

function isValidGeminiApiKeyFormat(key) {
  const trimmed = (key || "").trim().replace(/\s+/g, "");
  return (
    (trimmed.startsWith("AIza") && trimmed.length >= 30) ||
    (trimmed.startsWith("AQ.") && trimmed.length >= 20)
  );
}

function getGeminiKeyError(key) {
  const trimmed = (key || "").trim();
  if (!trimmed) {
    return "Paste your Gemini API key in Settings before uploading.";
  }
  if (!isValidGeminiApiKeyFormat(trimmed)) {
    return (
      "That does not look like a Google AI Studio API key. " +
      "Create one at aistudio.google.com/apikey — keys start with AIza or AQ."
    );
  }
  return "";
}

function getSelectedModel() {
  if (providerSelect.value === "gemini") {
    return geminiModelSelect.value || "";
  }
  return modelSelect.value || "";
}

function setSettingsStatus(message, isError = false) {
  settingsStatus.textContent = message;
  settingsStatus.classList.toggle("error", isError);
}

function toggleProviderFields() {
  const useGemini = providerSelect.value === "gemini";
  geminiKeyGroup.classList.toggle("hidden", !useGemini);
  geminiModelField.classList.toggle("hidden", !useGemini);
  modelField.classList.toggle("hidden", useGemini);
}

function renderGeminiModels(models, preferredModel, fallbackModel = "") {
  geminiModelSelect.innerHTML = "";

  if (!models.length) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "No Gemini models configured";
    geminiModelSelect.appendChild(option);
    return;
  }

  models.forEach((model) => {
    const option = document.createElement("option");
    option.value = model.id;
    option.textContent = model.label;
    geminiModelSelect.appendChild(option);
  });

  const candidate = isGeminiModel(preferredModel)
    ? preferredModel
    : isGeminiModel(fallbackModel)
      ? fallbackModel
      : GEMINI_DEFAULT_MODEL;

  if (candidate && models.some((model) => model.id === candidate)) {
    geminiModelSelect.value = candidate;
  }
}

function renderOllamaModels(models, preferredModel) {
  modelSelect.innerHTML = "";

  if (!models.length) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "No models found — run: ollama pull <model>";
    modelSelect.appendChild(option);
    return;
  }

  models.forEach((model) => {
    const option = document.createElement("option");
    option.value = model.id;
    option.textContent = model.label;
    modelSelect.appendChild(option);
  });

  if (preferredModel && models.some((model) => model.id === preferredModel)) {
    modelSelect.value = preferredModel;
  }
}

async function loadSettings({ preserveProvider = false } = {}) {
  try {
    const provider = preserveProvider
      ? providerSelect.value || "ollama"
      : providerSelect.value || "ollama";
    const [settingsRes, modelsRes, healthRes] = await Promise.all([
      fetch("/api/settings"),
      fetch(`/api/models?provider=${encodeURIComponent(provider)}&t=${Date.now()}`),
      fetch("/api/health"),
    ]);

    const settings = await settingsRes.json();
    const modelsData = await modelsRes.json();
    const health = await healthRes.json();

    if (health.api_version !== 2) {
      setSettingsStatus(
        "Outdated server detected. Close extra terminals and run: .\\scripts\\start_server.ps1",
        true,
      );
    }

    if (!preserveProvider) {
      providerSelect.value = settings.llm_provider || "ollama";
    }
    toggleProviderFields();

    if (providerSelect.value === "gemini") {
      renderGeminiModels(
        modelsData.models || [],
        settings.default_model,
        modelsData.default || GEMINI_DEFAULT_MODEL,
      );
    } else {
      renderOllamaModels(modelsData.models || [], settings.default_model || modelsData.default);
    }

    if (settings.gemini_api_key_set && settings.gemini_api_key_preview) {
      savedGeminiKeyValid =
        typeof settings.gemini_api_key_valid === "boolean"
          ? settings.gemini_api_key_valid
          : true;
      if (savedGeminiKeyValid) {
        geminiKeyPreview.textContent = ` Saved key: ${settings.gemini_api_key_preview}`;
      } else {
        geminiKeyPreview.textContent = " Saved key looks invalid — must start with AIza or AQ.";
      }
    } else {
      savedGeminiKeyValid = false;
      geminiKeyPreview.textContent = "";
    }

    const count =
      providerSelect.value === "gemini"
        ? `${(modelsData.models || []).length} Gemini model(s) available`
        : `${(modelsData.models || []).length} Ollama model(s) from this machine`;
    setSettingsStatus(`Settings loaded. ${count}.`);
  } catch (err) {
    setSettingsStatus(`Could not load settings: ${err.message}`, true);
  }
}

async function saveSettings() {
  saveSettingsBtn.disabled = true;
  setSettingsStatus("Saving…");

  try {
    if (providerSelect.value === "gemini" && geminiApiKey.value.trim()) {
      const keyError = getGeminiKeyError(geminiApiKey.value);
      if (keyError) {
        throw new Error(keyError);
      }
    }

    const res = await fetch("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        llm_provider: providerSelect.value,
        default_model: getSelectedModel(),
        gemini_api_key: geminiApiKey.value,
        clear_gemini_api_key: false,
      }),
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Failed to save settings.");
    }

    geminiApiKey.value = "";
    if (data.gemini_api_key_set && data.gemini_api_key_preview) {
      geminiKeyPreview.textContent = ` Saved key: ${data.gemini_api_key_preview}`;
    }

    await loadSettings({ preserveProvider: true });
    setSettingsStatus("Settings saved to .env");
  } catch (err) {
    setSettingsStatus(err.message, true);
  } finally {
    saveSettingsBtn.disabled = false;
  }
}

function renderList(targetId, items) {
  const list = document.getElementById(targetId);
  list.innerHTML = "";
  items.forEach((item) => {
    const li = document.createElement("li");
    li.textContent = item;
    list.appendChild(li);
  });
}

function renderCategories(categories) {
  const container = document.getElementById("categoriesList");
  container.innerHTML = "";

  categories.forEach((cat) => {
    const pct = cat.max ? Math.min(100, (cat.score / cat.max) * 100) : 0;
    const row = document.createElement("div");
    row.className = "category-row";
    row.innerHTML = `
      <div class="category-top">
        <span>${cat.label}</span>
        <strong>${cat.score}/${cat.max}</strong>
      </div>
      <div class="bar"><div class="bar-fill" style="width:${pct}%"></div></div>
      <p class="evidence">${cat.evidence}</p>
    `;
    container.appendChild(row);
  });
}

function renderAdjustments(bonus, deductions) {
  const container = document.getElementById("adjustments");
  container.innerHTML = "";

  if (bonus && bonus.total) {
    const el = document.createElement("div");
    el.className = "adjustment bonus";
    el.innerHTML = `<strong>Bonus: +${bonus.total}</strong><span>${bonus.breakdown || ""}</span>`;
    container.appendChild(el);
  }

  if (deductions && deductions.total) {
    const el = document.createElement("div");
    el.className = "adjustment deduction";
    el.innerHTML = `<strong>Deductions: -${deductions.total}</strong><span>${deductions.reasons || ""}</span>`;
    container.appendChild(el);
  }

  if (!container.children.length) {
    container.innerHTML = "<p class='evidence'>No bonus or deductions applied.</p>";
  }
}

function renderResults(data) {
  document.getElementById("candidateName").textContent = data.candidate_name || "Candidate";
  document.getElementById("finalScore").textContent = data.overall.final_score;
  document.getElementById("maxScore").textContent = data.overall.category_max;

  const cacheNote = document.getElementById("cacheNote");
  cacheNote.classList.toggle("hidden", !data.from_cache);

  const resultsModel = document.getElementById("resultsModel");
  if (data.model) {
    resultsModel.textContent = `Scored with: ${data.model}`;
    resultsModel.classList.remove("hidden");
  } else {
    resultsModel.classList.add("hidden");
  }

  renderCategories(data.categories || []);
  renderAdjustments(data.bonus_points, data.deductions);
  renderList("strengthsList", data.key_strengths || []);
  renderList("improvementsList", data.areas_for_improvement || []);

  show(resultsSection);
}

async function evaluateFile(file) {
  if (!file || !file.name.toLowerCase().endsWith(".pdf")) {
    document.getElementById("errorMessage").textContent = "Please upload a PDF file.";
    show(errorSection);
    return;
  }

  const provider = providerSelect.value;
  const model = getSelectedModel();

  if (!model) {
    settingsSection.classList.remove("hidden");
    setSettingsStatus("Select a model in Settings before evaluating.", true);
    return;
  }

  if (provider === "gemini") {
    const pastedKey = geminiApiKey.value.trim();
    const keyError = pastedKey
      ? getGeminiKeyError(pastedKey)
      : savedGeminiKeyValid
        ? ""
        : "Paste a valid Google AI Studio API key (starts with AIza or AQ.) before uploading.";
    if (keyError) {
      settingsSection.classList.remove("hidden");
      setSettingsStatus(keyError, true);
      document.getElementById("errorMessage").textContent = keyError;
      show(errorSection);
      return;
    }
  }

  show(loadingSection);
  document.getElementById("loadingFile").textContent = `${file.name} · ${model} (${provider})`;

  const formData = new FormData();
  formData.append("file", file);
  formData.append("model", model);
  formData.append("provider", provider);
  formData.append("gemini_api_key", geminiApiKey.value.trim());

  try {
    const res = await fetch("/api/evaluate", {
      method: "POST",
      body: formData,
    });

    const raw = await res.text();
    let data = {};
    try {
      data = raw ? JSON.parse(raw) : {};
    } catch {
      throw new Error(raw.slice(0, 300) || `Request failed (${res.status})`);
    }

    if (!res.ok) {
      const detail = data.detail;
      const message = Array.isArray(detail)
        ? detail.map((item) => item.msg || item).join(" ")
        : detail || "Evaluation failed.";
      throw new Error(message);
    }

    renderResults(data);
  } catch (err) {
    let message = err.message || "Evaluation failed.";
    if (message === "Failed to fetch") {
      message = "Could not reach the server. Make sure it is running at http://127.0.0.1:8000";
    }
    document.getElementById("errorMessage").textContent = message;
    show(errorSection);
  }
}

settingsToggle.addEventListener("click", () => {
  settingsSection.classList.toggle("hidden");
});

providerSelect.addEventListener("change", async () => {
  toggleProviderFields();
  await loadSettings({ preserveProvider: true });
});

saveSettingsBtn.addEventListener("click", saveSettings);
refreshModelsBtn.addEventListener("click", () => loadSettings({ preserveProvider: true }));
browseBtn.addEventListener("click", () => fileInput.click());
retryBtn.addEventListener("click", reset);
newEvalBtn.addEventListener("click", reset);

fileInput.addEventListener("change", (e) => {
  const file = e.target.files[0];
  if (file) evaluateFile(file);
});

dropzone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropzone.classList.add("dragover");
});

dropzone.addEventListener("dragleave", () => {
  dropzone.classList.remove("dragover");
});

dropzone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropzone.classList.remove("dragover");
  const file = e.dataTransfer.files[0];
  if (file) evaluateFile(file);
});

settingsSection.classList.remove("hidden");
loadSettings();
