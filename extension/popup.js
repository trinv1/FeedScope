//Promise is a placeholder for a value that is
//  not yet available but will be in the future
const statusEl = document.getElementById("status");
const API_BASE = "echochamber-production-573f.up.railway.app";

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
async function fetchStudies(token) {
  const res = await fetch(`${API_BASE}/studies`, {
  headers: {
        Authorization: `Bearer ${token}`
    }
  });
  if (!res.ok) throw new Error("Failed to load studies");
  return (await res.json()).studies;
}

//Calling subjects of study belonging to owner
async function fetchSubjects(token, studyId) {
  const url = new URL(`${API_BASE}/subjects`);
  if (studyId) url.searchParams.set("study_id", studyId);

  const res = await fetch(url, {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
  if (!res.ok) throw new Error("Failed to load subjects");
  return (await res.json()).subjects;
}

//Calling phases of study belonging to owner
async function fetchPhases(token, studyId) {
  const url = new URL(`${API_BASE}/phases`);
  if (studyId) url.searchParams.set("study_id", studyId);

  const res = await fetch(url, {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
  if (!res.ok) throw new Error("Failed to load phases");
  return (await res.json()).phases;
}

//Populating study dropdown on popup load in accordance of owner
async function populateStudies(token) {
  const studySelect = document.getElementById("studyId");
  studySelect.innerHTML = `<option value="">Select study</option>`;

  if (!token) return;

  const studies = await fetchStudies(token);
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
async function populateSubjects(token, studyId) {
  const subjectSelect = document.getElementById("subjectId");
  subjectSelect.innerHTML = `<option value="">Select subject</option>`;

  if (!token || !studyId) return;

  const subjects = await fetchSubjects(token, studyId);
  for (const subject of subjects) {
    const option = document.createElement("option");
    option.value = subject.subject_id;
    option.textContent = subject.label || subject.subject_id;
    subjectSelect.appendChild(option);
  }
}

//Populating phases dropdown
async function populatePhases(token, studyId) {
  const phaseSelect = document.getElementById("phaseId");
  phaseSelect.innerHTML = `<option value="">Select phase</option>`;

  if (!token || !studyId) return;

  const phases = await fetchPhases(token, studyId);
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

    //Saving auth token in browser extension local storage
    await chrome.storage.local.set({
      authToken: result.token
    });

    document.getElementById("authToken").value = result.token;

    const me = await fetchMe(result.token);
    await populateStudies(result.token);

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

//Study id changing based on auth token and propogates changes to subjects and phases
document.getElementById("studyId").addEventListener("change", async (e) => {
  try {
    const token = document.getElementById("authToken").value.trim();
    const studyId = e.target.value;

    await populateSubjects(token, studyId);
    await populatePhases(token, studyId);
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
      await populateStudies(saved.authToken);
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

  const studyId = document.getElementById("studyId").value.trim();
  const subjectId = document.getElementById("subjectId").value.trim();
  const phaseId = document.getElementById("phaseId").value.trim();
  
  let sessionId = document.getElementById("sessionId").value.trim();
  if (!sessionId) {
    sessionId = `session_${Date.now()}`;
    document.getElementById("sessionId").value = sessionId;
  }
  
  //Sending START message to background service worker
  await chrome.runtime.sendMessage({
    type: "START",
    tabId: tab.id,
    captureEveryMs: 2000,
    authToken,
    studyId,
    subjectId,
    phaseId,
  });

  //Updating popup status
  statusEl.textContent = "Running";
}); 

//Runs when stop button is clicked
document.getElementById("stop").addEventListener("click", async () => {
  const tab = await getActiveTab();
  if (!tab || !tab.id) return;

  await chrome.runtime.sendMessage({ type: "STOP", tabId: tab.id });
  statusEl.textContent = "Stopped";
});
