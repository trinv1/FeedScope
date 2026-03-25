//Promise is a placeholder for a value that is
//  not yet available but will be in the future

const API_BASE = "https://echochamber-q214.onrender.com";

//Calling studies
async function fetchStudies() {
  const res = await fetch(`${API_BASE}/studies`);
  if (!res.ok) throw new Error("Failed to load studies");
  const data = await res.json();
  return data.studies;
}

//Calling subjects of study
async function fetchSubjects(studyId) {
  const url = new URL(`${API_BASE}/subjects`);
  if (studyId) url.searchParams.set("study_id", studyId);

  const res = await fetch(url);
  if (!res.ok) throw new Error("Failed to load subjects");
  const data = await res.json();
  return data.subjects;
}

//Calling phases of study
async function fetchPhases(studyId) {
  const url = new URL(`${API_BASE}/phases`);
  if (studyId) url.searchParams.set("study_id", studyId);

  const res = await fetch(url);
  if (!res.ok) throw new Error("Failed to load phases");
  const data = await res.json();
  return data.phases;
}

const statusEl = document.getElementById("status");

//Populating study dropdown on popup load
async function populateStudies() {
  const studySelect = document.getElementById("studyId");
  studySelect.innerHTML = `<option value="">Select study</option>`;

  const studies = await fetchStudies();
  for (const study of studies) {
    const option = document.createElement("option");
    if (typeof study === "string") {
      option.value = study;
      option.textContent = study;
    } else {
      option.value = study.study_id;
      option.textContent = study.name || study.study_id;
    }
    studySelect.appendChild(option);
  }
}

//Populating subjects dropdown
async function populateSubjects(studyId) {
  const subjectSelect = document.getElementById("subjectId");
  subjectSelect.innerHTML = `<option value="">Select subject</option>`;

  const subjects = await fetchSubjects(studyId);
  for (const subject of subjects) {
    const option = document.createElement("option");
    option.value = subject.subject_id;
    option.textContent = subject.label || subject.subject_id;
    subjectSelect.appendChild(option);
  }
}

//Populating phases dropdown
async function populatePhases(studyId) {
  const phaseSelect = document.getElementById("phaseId");
  phaseSelect.innerHTML = `<option value="">Select phase</option>`;

  const phases = await fetchPhases(studyId);
  for (const phase of phases) {
    const option = document.createElement("option");
    option.value = phase.phase_id;
    option.textContent = phase.label || phase.phase_id;
    phaseSelect.appendChild(option);
  }
}

//Run when study dropdown changes
document.getElementById("studyId").addEventListener("change", async (e) => {
  const studyId = e.target.value;
  await populateSubjects(studyId);
  await populatePhases(studyId);
});

//Returning currently open tab
async function getActiveTab() {
  //getting first item from array and calling it tab
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab;
}

//Runs when start button is clicked
document.getElementById("start").addEventListener("click", async () => {
  const tab = await getActiveTab();
  if (!tab || !tab.id) return;
  
  const studyId = document.getElementById("studyId").value.trim();
  const subjectId = document.getElementById("subjectId").value.trim();
  const phaseId = document.getElementById("phaseId").value.trim();
  const sessionId = document.getElementById("sessionId").value.trim();
  
  await chrome.runtime.sendMessage({
    type: "START",
    tabId: tab.id,
    captureEveryMs: 2000,
    studyId,
    subjectId,
    phaseId,
    sessionId
  });

  statusEl.textContent = "Running";
}); 

//Runs when stop button is clicked
document.getElementById("stop").addEventListener("click", async () => {
  const tab = await getActiveTab();
  if (!tab || !tab.id) return;

  await chrome.runtime.sendMessage({ type: "STOP", tabId: tab.id });
  statusEl.textContent = "Stopped";
});

//Populating studies when popup loads
document.addEventListener("DOMContentLoaded", async () => {
  try {
    await populateStudies();
  } catch (e) {
    console.error("Failed to initialise popup:", e);
    statusEl.textContent = "Failed to load study data";
  }
});