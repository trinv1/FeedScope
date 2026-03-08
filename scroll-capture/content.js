let running = false;
let rafId = null;

let speed = 120; //px/sec (changes over time)
let lastTs = 0;
let pausedUntil = 0;

let timer = null;

let tempoUntil = 0;
let tempoMult = 1;

//Random phase durations
function randBetween(a, b) { 
  return a + Math.random() * (b - a)
}

function detectActiveUsername() {
  const pageText = document.body.innerText.toLowerCase();

  if (pageText.includes("@briansmith2211")) return "boy";
  if (pageText.includes("@rachelsmith221")) return "girl";

  return "unknown";
}

//Update scrolling time
function frameUpdate(ts){
    if (!running) return;

    if (!lastTs) lastTs = ts;
    const dt = (ts - lastTs) / 1000;//s since previous frame update
    lastTs = ts;

  //Pause randomly
  if (Date.now() < pausedUntil) {
    rafId = requestAnimationFrame(frameUpdate);
    return;
  }
  if (Math.random() < 0.008) { //condition is true about 2% of frames
    pausedUntil = Date.now() + (200 + Math.random() * 800);//pause length: 0.2–1 second
    rafId = requestAnimationFrame(frameUpdate);
    return;
  }

  //Wander speed a bit
  speed += (Math.random() * 2 - 1) * 70 * dt;
  speed = Math.max(200, Math.min(500, speed));  //never above 400 never below 60

  //Occasionally entering a "tempo" phase (slow browse/normal/fast burst)
  if (Date.now() > tempoUntil && Math.random() < 0.015) {
    const r = Math.random();
    if (r < 0.30) tempoMult = randBetween(0.55, 0.85);  
    else if (r < 0.90) tempoMult = randBetween(0.95, 1.25); 
    else tempoMult = randBetween(1.55, 1.85);            

    tempoUntil = Date.now() + randBetween(500, 2200); //lasts 0.5–2.2s
  }

  window.scrollBy(0, speed * tempoMult * dt);//scroll down only
  rafId = requestAnimationFrame(frameUpdate);
}

//Listens for messages from background/popup.js
chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.type == "GET_ACTIVE_ACCOUNT") {
    const account = detectActiveUsername();
    sendResponse({ account });
    return true;
  }
  
  if (msg.type == "START_SCROLL"){
    running = true;
    lastTs = 0;
    pausedUntil = 0;
    if (!rafId) rafId = requestAnimationFrame(frameUpdate);
    sendResponse({ ok: true });
  }

  if (msg.type == "STOP_SCROLL") {
    running = false;
    if (rafId) cancelAnimationFrame(rafId);
    rafId = null;
    sendResponse({ ok: true });
    return;
  }
});
