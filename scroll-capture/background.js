let currentTabId = null;
let captureTimer = null;
let capturingTabId = null;
let isUploading = false; // prevents overlapping uploads
let backoffUntil = 0; // timestamp (ms). If now < this, skip attempts.

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

//Upload one capture to Render
async function uploadToRender({ dataUrl, tabId, pageUrl, account }) {
  const blob = await dataUrlToBlob(dataUrl);

  const form = new FormData();
  form.append("image", blob, `${new Date().toISOString()}.jpg`);
  form.append("tabId", String(tabId));
  form.append("pageUrl", pageUrl ?? "");
  form.append("ts", String(Date.now()));
  form.append("account", account || "unknown");

  const res = await fetch("https://echochamber-q214.onrender.com/upload", {
    method: "POST",
    body: form
  });

  if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
  return await res.json().catch(() => ({}));
}

//Start capture+upload loop
async function startCaptureLoop(tabId, intervalMs = 1500) {
  stopCaptureLoop();
  capturingTabId = tabId;

  captureTimer = setInterval(async () => {
    //avoid overlapping uploads if network is slow
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

      const detectedAccount = response?.account ?? "unknown";
      console.log("Detected account:", detectedAccount, "URL:", tab.url);

      await uploadToRender({
        dataUrl,
        tabId: capturingTabId,
        pageUrl: tab.url,
        account: detectedAccount
      });
    } catch (e) {
      console.warn("Capture/upload failed:", e);
      backoffUntil = Date.now() + 3000; //wait 3 seconds after a failure
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

//Listening for message to start or stop scrolling from popup.js
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  (async () => {
    if (msg.type == "START") {
      currentTabId = msg.tabId;
      await ensureContentScript(currentTabId);
      await chrome.tabs.sendMessage(currentTabId, { type: "START_SCROLL" });
    
    //start capturing + uploading
      await startCaptureLoop(currentTabId, msg.captureEveryMs ?? 1000);
    }

    if (msg.type == "STOP") {
      const tabId = msg.tabId ?? currentTabId
      if (!tabId) return; 
     await chrome.tabs.sendMessage(tabId, { type: "STOP_SCROLL" });
    stopCaptureLoop();
    }
  })();
  return true;
});
