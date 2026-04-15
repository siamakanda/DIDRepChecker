// background.js - Handles API calls with fallback URLs and storage

// Default API URLs (user can modify via popup)
let apiUrls = ["http://localhost:5000/scrape"];

// Load stored URLs on startup
chrome.storage.local.get(["apiUrls"], (result) => {
  if (result.apiUrls && Array.isArray(result.apiUrls) && result.apiUrls.length > 0) {
    apiUrls = result.apiUrls;
  }
});

// Listen for messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "getNumbersFromPage") {
    // Forward to content script to extract numbers
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (!tabs[0]) {
        sendResponse({ error: "No active tab" });
        return;
      }
      chrome.tabs.sendMessage(tabs[0].id, { action: "extractNumbers" }, (response) => {
        if (chrome.runtime.lastError) {
          sendResponse({ error: chrome.runtime.lastError.message });
        } else {
          sendResponse(response);
        }
      });
    });
    return true; // async response
  }
  else if (request.action === "selectNumbersOnPage") {
    // Forward selection list to content script
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (!tabs[0]) {
        sendResponse({ error: "No active tab" });
        return;
      }
      chrome.tabs.sendMessage(tabs[0].id, { action: "selectNumbers", numbers: request.numbers }, (response) => {
        if (chrome.runtime.lastError) {
          sendResponse({ error: chrome.runtime.lastError.message });
        } else {
          sendResponse(response);
        }
      });
    });
    return true;
  }
  else if (request.action === "callApi") {
    // Call reputation API with fallback URLs
    callApiWithFallback(request.numbers).then(results => {
      sendResponse({ success: true, data: results });
    }).catch(err => {
      sendResponse({ success: false, error: err.message });
    });
    return true;
  }
  else if (request.action === "saveApiUrls") {
    apiUrls = request.urls;
    chrome.storage.local.set({ apiUrls: apiUrls }, () => {
      sendResponse({ success: true });
    });
    return true;
  }
  else if (request.action === "getApiUrls") {
    sendResponse({ urls: apiUrls });
    return true;
  }
});

async function callApiWithFallback(numbers) {
  let lastError = null;
  for (let url of apiUrls) {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 120000); // 2 min timeout
      const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ numbers: numbers }),
        signal: controller.signal
      });
      clearTimeout(timeoutId);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const data = await response.json();
      return data; // success
    } catch (err) {
      lastError = err;
      console.warn(`API call to ${url} failed: ${err.message}`);
      // continue to next URL
    }
  }
  throw new Error(`All API endpoints failed. Last error: ${lastError?.message}`);
}