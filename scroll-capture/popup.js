//Promise is a placeholder for a value that is
//  not yet available but will be in the future
const statusEl = document.getElementById("status");
const API_BASE = "https://echochamber-q214.onrender.com";

//Login helper
async function loginExtension(email, password) {
  const formData = new FormData();
  formData.append("email", email);
  formData.append("password", password);

  const res = await fetch(`${API_BASE}/login`, {
    method: "POST",
    body: formData
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Login failed: ${res.status} ${text}`);
  }

  return await res.json();
}

//Calling me endpoint to fetch token
async function fetchMe(token) {
  const res = await fetch(`${API_BASE}/me`, {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });

  if (!res.ok) throw new Error("Failed to load current user");
  return await res.json();
}

//Calling studies belonging to owner
async function fetchStudies(ownerId) {
  const url = new URL(`${API_BASE}/studies`);
  if (ownerId) url.searchParams.set("owner_id", ownerId);

  const res = await fetch(url);
  if (!res.ok) throw new Error("Failed to load studies");
  return (await res.json()).studies;
}

//Calling subjects of study belonging to owner
async function fetchSubjects(ownerId, studyId) {
  const url = new URL(`${API_BASE}/subjects`);
  if (ownerId) url.searchParams.set("owner_id", ownerId);
  if (studyId) url.searchParams.set("study_id", studyId);

  const res = await fetch(url);
  if (!res.ok) throw new Error("Failed to load subjects");
  return (await res.json()).subjects;
}

//Calling phases of study belonging to owner
async function fetchPhases(ownerId, studyId) {
  const url = new URL(`${API_BASE}/phases`);
  if (ownerId) url.searchParams.set("owner_id", ownerId);
  if (studyId) url.searchParams.set("study_id", studyId);

  const res = await fetch(url);
  if (!res.ok) throw new Error("Failed to load phases");
  return (await res.json()).phases;
}

//Populating study dropdown on popup load in accordance of owner
async function populateStudies(ownerId) {
  const studySelect = document.getElementById("studyId");
  studySelect.innerHTML = `<option value="">Select study</option>`;

  if (!ownerId) return;

  const studies = await fetchStudies(ownerId);
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
async function populateSubjects(ownerId, studyId) {
  const subjectSelect = document.getElementById("subjectId");
  subjectSelect.innerHTML = `<option value="">Select subject</option>`;

  if (!ownerId || !studyId) return;

  const subjects = await fetchSubjects(ownerId, studyId);
  for (const subject of subjects) {
    const option = document.createElement("option");
    option.value = subject.subject_id;
    option.textContent = subject.label || subject.subject_id;
    subjectSelect.appendChild(option);
  }
}

//Populating phases dropdown
async function populatePhases(ownerId, studyId) {
  const phaseSelect = document.getElementById("phaseId");
  phaseSelect.innerHTML = `<option value="">Select phase</option>`;

  if (!ownerId || !studyId) return;

  const phases = await fetchPhases(ownerId, studyId);
  for (const phase of phases) {
    const option = document.createElement("option");
    option.value = phase.phase_id;
    option.textContent = phase.label || phase.phase_id;
    phaseSelect.appendChild(option);
  }
}

//Login button handler
document.getElementById("login").addEventListener("click", async () => {
  try {
    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value.trim();

    const result = await loginExtension(email, password);

    await chrome.storage.local.set({
      authToken: result.token
    });

    document.getElementById("authToken").value = result.token;

    const me = await fetchMe(result.token);
    await populateStudies(me.user_id);

    document.getElementById("subjectId").innerHTML = `<option value="">Select subject</option>`;
    document.getElementById("phaseId").innerHTML = `<option value="">Select phase</option>`;

    statusEl.textContent = `Logged in as ${me.email}`;
  } catch (e) {
    console.error(e);
    statusEl.textContent = "Login failed";
  }
});

//Clearing stored token and resetting dropdown
document.getElementById("logout").addEventListener("click", async () => {
  await chrome.storage.local.remove(["authToken"]);

  document.getElementById("authToken").value = "";
  document.getElementById("email").value = "";
  document.getElementById("password").value = "";

  document.getElementById("studyId").innerHTML = `<option value="">Select study</option>`;
  document.getElementById("subjectId").innerHTML = `<option value="">Select subject</option>`;
  document.getElementById("phaseId").innerHTML = `<option value="">Select phase</option>`;

  statusEl.textContent = "Logged out";
});

//Listening for when the authentication token changes
document.getElementById("authToken").addEventListener("change", async () => {
  try {
    const token = document.getElementById("authToken").value.trim();
    await chrome.storage.local.set({ authToken: token });

    const me = await fetchMe(token);
    await populateStudies(me.user_id);

    document.getElementById("subjectId").innerHTML = `<option value="">Select subject</option>`;
    document.getElementById("phaseId").innerHTML = `<option value="">Select phase</option>`;
  } catch (e) {
    console.error("Failed to load user from token:", e);
  }
});

//Study id changing based on auth token and propogates changes to subjects and phases
document.getElementById("studyId").addEventListener("change", async (e) => {
  try {
    const token = document.getElementById("authToken").value.trim();
    const me = await fetchMe(token);
    const ownerId = me.user_id;
    const studyId = e.target.value;

    await populateSubjects(ownerId, studyId);
    await populatePhases(ownerId, studyId);
  } catch (e) {
    console.error("Failed to load subjects/phases:", e);
  }
});

//Populating studies using auth token when popup loads
document.addEventListener("DOMContentLoaded", async () => {
  try {
    const saved = await chrome.storage.local.get(["authToken"]);
    if (saved.authToken) {
      document.getElementById("authToken").value = saved.authToken;
      const me = await fetchMe(saved.authToken);
      await populateStudies(me.user_id);
      statusEl.textContent = `Logged in as ${me.email}`;
    }
  } catch (e) {
    console.error("Failed to initialise popup:", e);
    statusEl.textContent = "Not logged in";
  }
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
  
  const authToken = document.getElementById("authToken").value.trim();
  await chrome.storage.local.set({ authToken });

  const me = await fetchMe(authToken);
  const ownerId = me.user_id;

  const studyId = document.getElementById("studyId").value.trim();
  const subjectId = document.getElementById("subjectId").value.trim();
  const phaseId = document.getElementById("phaseId").value.trim();
  
  let sessionId = document.getElementById("sessionId").value.trim();
  if (!sessionId) {
    sessionId = `session_${Date.now()}`;
    document.getElementById("sessionId").value = sessionId;
  }
  
  await chrome.runtime.sendMessage({
    type: "START",
    tabId: tab.id,
    captureEveryMs: 2000,
    ownerId,
    studyId,
    subjectId,
    phaseId,
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
