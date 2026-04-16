// background.js – Service worker: API calls, storage, message routing

let apiUrls = ["http://localhost:5000/scrape"];

// Load stored API URLs
chrome.storage.local.get(["apiUrls"], (result) => {
    if (result.apiUrls && Array.isArray(result.apiUrls) && result.apiUrls.length) {
        apiUrls = result.apiUrls;
    }
});

// Save API URLs when updated from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "saveApiUrls") {
        apiUrls = request.urls;
        chrome.storage.local.set({ apiUrls: apiUrls });
        sendResponse({ success: true });
        return true;
    }
    else if (request.action === "getApiUrls") {
        sendResponse({ urls: apiUrls });
        return true;
    }
    else if (request.action === "callReputationApi") {
        callApiWithFallback(request.numbers, sendResponse);
        return true;
    }
    else if (request.action === "storeCapturedNumbers") {
        chrome.storage.local.set({ capturedNumbers: request.numbers });
        sendResponse({ success: true });
        return true;
    }
    else if (request.action === "getCapturedNumbers") {
        chrome.storage.local.get(["capturedNumbers"], (result) => {
            sendResponse({ numbers: result.capturedNumbers || [] });
        });
        return true;
    }
    else if (request.action === "storeApiResults") {
        chrome.storage.local.set({ apiResults: request.results });
        sendResponse({ success: true });
        return true;
    }
    else if (request.action === "getApiResults") {
        chrome.storage.local.get(["apiResults"], (result) => {
            sendResponse({ results: result.apiResults || [] });
        });
        return true;
    }
    else if (request.action === "clearStoredData") {
        chrome.storage.local.remove(["apiResults", "capturedNumbers"]);
        sendResponse({ success: true });
        return true;
    }
    else if (request.action === "selectNumbersOnPage") {
        // Forward to content script
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
});

async function callApiWithFallback(numbers, sendResponse) {
    let lastError = null;
    for (let url of apiUrls) {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 120000);
            const response = await fetch(url, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ numbers: numbers }),
                signal: controller.signal
            });
            clearTimeout(timeoutId);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();
            sendResponse({ success: true, data: data });
            return;
        } catch (err) {
            lastError = err;
            console.warn(`API call to ${url} failed: ${err.message}`);
        }
    }
    sendResponse({ success: false, error: lastError?.message || "All endpoints failed" });
}