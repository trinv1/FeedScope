let currentTabId = null;
let captureTimer = null;
let capturingTabId = null;
let isUploading = false; // prevents overlapping uploads
let backoffUntil = 0; // timestamp (ms). If now < this, skip attempts.

let currentOwnerId = "";
let currentStudyId = "";
let currentSubjectId = "";
let currentPhaseId = "";
let currentSessionId = "";

//Injecting content.js into current tab
async function ensureContentScript(tabId) {
  await chrome.scripting.executeScript({
    target: { tabId },
    files: ["content.js"]
  });
}

//Fetching data url and converting to binary
async function dataUrlToBlob(dataUrl) {
  return await (await fetch(dataUrl)).blob();
}

//Getting stored auth token
async function getStoredAuthToken() {
  const saved = await chrome.storage.local.get(["authToken"]);
  return saved.authToken || "";
}

//Upload one capture to Render
async function uploadToRender(dataUrl, tabId, pageUrl, ts, studyId, subjectId, phaseId, sessionId) {
  const authToken = await getStoredAuthToken();
  if (!authToken) {
    throw new Error("Missing auth token");
  }
  
  const blob = await (await fetch(dataUrl)).blob();

  //Creating form object and appending items 
  const formData = new FormData();
  formData.append("image", blob, "capture.png");
  formData.append("tabId", String(tabId ?? ""));
  formData.append("pageUrl", pageUrl ?? "");
  formData.append("ts", ts ?? "");
  formData.append("studyId", studyId ?? "");
  formData.append("subjectId", subjectId ?? "");
  formData.append("phaseId", phaseId ?? "");
  formData.append("sessionId", sessionId ?? "");

  //Sending POST request with token to upload endpoint
  const res = await fetch("echochamber-production-573f.up.railway.app/upload", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${authToken}`
    },
    body: formData
  });

  if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
  return await res.json().catch(() => ({}));
}

//Upload session start of session to render
async function startSession(studyId, subjectId, phaseId) {
  const authToken = await getStoredAuthToken();
  if (!authToken) {
    throw new Error("Missing auth token");
  }
  
  const formData = new FormData();
  formData.append("study_id", studyId);
  formData.append("subject_id", subjectId);
  formData.append("phase_id", phaseId);
  formData.append("session_id", `session_${Date.now()}`);
  formData.append("label", "Extension capture run");

  //Sending authenticated POST request to endpoint
  const res = await fetch("echochamber-production-573f.up.railway.app/sessions/start", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${authToken}`
    },
    body: formData
  });

  if (!res.ok) {
    throw new Error(`Failed to start session: ${res.status}`);
  }

  return await res.json();
}

//Upload end of session to render
async function stopSession(studyId, sessionId) {
  const authToken = await getStoredAuthToken();
  if (!authToken) {
    throw new Error("Missing auth token");
  }

  const formData = new FormData();
  formData.append("study_id", studyId);
  formData.append("session_id", sessionId);

  const res = await fetch("echochamber-production-573f.up.railway.app/sessions/stop", {
    method: "POST",
    body: formData,
    headers: {
      Authorization: `Bearer ${authToken}`
    }, 
  });

  if (!res.ok) {
    throw new Error(`Failed to stop session: ${res.status}`);
  }

  return await res.json();
}

//Starting capture+upload loop
async function startCaptureLoop(tabId, intervalMs = 1500, studyId = "", subjectId = "", phaseId = "", sessionId = "") {
  stopCaptureLoop();
  capturingTabId = tabId;

  //Repeating timer
  captureTimer = setInterval(async () => {
    
    //Avoid overlapping uploads if network is slow
    if (isUploading) return;
      if (Date.now() < backoffUntil) return; //backoff active, skip this tick

    isUploading = true;

    try {
      const tab = await chrome.tabs.get(capturingTabId);

      //Capture visible tab in the window
      const dataUrl = await chrome.tabs.captureVisibleTab(tab.windowId, {
        format: "jpeg",
        quality: 70
      });

      const response = await chrome.tabs.sendMessage(capturingTabId, {
        type: "GET_ACTIVE_ACCOUNT"
      });

      if (response && response.account !== null && response.account !== undefined) {
        detectedAccount = response.account;
      } else {
        detectedAccount = "unknown";
      }
      const ts = new Date().toISOString();
      console.log("Detected account:", detectedAccount, "URL:", tab.url);

      const result = await uploadToRender(
        dataUrl,
        capturingTabId,
        tab.url,
        ts,
        studyId,
        subjectId || detectedAccount,
        phaseId,
        sessionId
      );
    console.log("Upload success:", result);
    } catch (e) {
      console.warn("Capture/upload failed:", e);
      backoffUntil = Date.now() + 3000;
    } finally {
      isUploading = false;
    }
  }, intervalMs);
}

//Stop capturing
function stopCaptureLoop() {
  if (captureTimer) clearInterval(captureTimer);
  captureTimer = null;
  capturingTabId = null;
  isUploading = false;
}

//Listening for start message from popup.js
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  (async () => {
    if (msg.type == "START") {
      //Storing incoming tab and study values in global variables
      currentTabId = msg.tabId;
      currentStudyId = msg.studyId ?? "";
      currentSubjectId = msg.subjectId ?? "";
      currentPhaseId = msg.phaseId ?? "";

      //Sending ids to session/start endpoint
      const sessionResult = await startSession(
        currentStudyId,
        currentSubjectId,
        currentPhaseId
    );

    //Storing sessionId returned from session/start endpoint
    currentSessionId = sessionResult.session_id;

    //Injecting content.js into active tab and sending message
    await ensureContentScript(currentTabId);
    await chrome.tabs.sendMessage(currentTabId, { type: "START_SCROLL" });
    
    //start capturing + uploading
      await startCaptureLoop(
        currentTabId,
        msg.captureEveryMs ?? 1000,
        currentStudyId,
        currentSubjectId,
        currentPhaseId,
        currentSessionId
    );
    }

    if (msg.type == "STOP") {
      const tabId = msg.tabId ?? currentTabId
      if (!tabId) return; 
     await chrome.tabs.sendMessage(tabId, { type: "STOP_SCROLL" });
    stopCaptureLoop();

    if (currentStudyId && currentSessionId) {
    await stopSession(currentStudyId, currentSessionId);
  }

  currentSessionId = "";
  }
  })();
  return true;
});
