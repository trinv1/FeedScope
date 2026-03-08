//Promise is a placeholder for a value that is
//  not yet available but will be in the future

const statusEl = document.getElementById("status");

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
  await chrome.runtime.sendMessage({ type: "START", tabId: tab.id, captureEveryMs: 2000 });
  statusEl.textContent = "Running";
});

//Runs when stop button is clicked
document.getElementById("stop").addEventListener("click", async () => {
  const tab = await getActiveTab();
  if (!tab || !tab.id) return;

  await chrome.runtime.sendMessage({ type: "STOP", tabId: tab.id });
  statusEl.textContent = "Stopped";
});
