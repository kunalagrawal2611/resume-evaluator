const uploadSection = document.getElementById("uploadSection");
const loadingSection = document.getElementById("loadingSection");
const errorSection = document.getElementById("errorSection");
const resultsSection = document.getElementById("resultsSection");
const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("fileInput");
const browseBtn = document.getElementById("browseBtn");
const retryBtn = document.getElementById("retryBtn");
const newEvalBtn = document.getElementById("newEvalBtn");
const modelBadge = document.getElementById("modelBadge");

function show(section) {
  [uploadSection, loadingSection, errorSection, resultsSection].forEach((el) => {
    el.classList.toggle("hidden", el !== section);
  });
}

function reset() {
  fileInput.value = "";
  show(uploadSection);
}

async function loadHealth() {
  try {
    const res = await fetch("/api/health");
    const data = await res.json();
    modelBadge.textContent = `Model: ${data.model}`;
  } catch {
    modelBadge.textContent = "Model: unavailable";
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

  show(loadingSection);
  document.getElementById("loadingFile").textContent = file.name;

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch("/api/evaluate", {
      method: "POST",
      body: formData,
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Evaluation failed.");
    }

    renderResults(data);
  } catch (err) {
    document.getElementById("errorMessage").textContent = err.message;
    show(errorSection);
  }
}

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

loadHealth();
