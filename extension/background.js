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
    else if (request.action === "startReputationCheck") {
        const isAppend = request.append || false;
        if (!isAppend) {
            chrome.storage.local.set({ apiResults: [] });
        }
        chrome.storage.local.set({ 
            apiState: { status: "running", progress: 0, total: request.numbers.length, error: null } 
        });
        callApiInChunks(request.numbers, isAppend);
        sendResponse({ success: true });
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

async function callApiInChunks(numbers, isAppend = false) {
    const CHUNK_SIZE = 100;
    let accumulatedResults = [];
    
    if (isAppend) {
        // Retrieve current results and filter out the numbers we are retrying
        const res = await chrome.storage.local.get(["apiResults"]);
        accumulatedResults = res.apiResults || [];
        accumulatedResults = accumulatedResults.filter(r => !numbers.includes(r.phone_number));
    }
    
    for (let i = 0; i < numbers.length; i += CHUNK_SIZE) {
        const chunk = numbers.slice(i, i + CHUNK_SIZE);
        let chunkSuccess = false;
        let lastError = null;
        
        for (let url of apiUrls) {
            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 120000);
                const response = await fetch(url, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ numbers: chunk }),
                    signal: controller.signal
                });
                clearTimeout(timeoutId);
                if (!response.ok) throw new Error(`HTTP ${response.status}`);
                
                const data = await response.json();
                accumulatedResults = accumulatedResults.concat(data);
                
                // Save accumulated results incrementally
                await chrome.storage.local.set({
                    apiResults: accumulatedResults,
                    apiState: { 
                        status: "running", 
                        progress: Math.min(i + CHUNK_SIZE, numbers.length), 
                        total: numbers.length, 
                        error: null 
                    }
                });
                
                chunkSuccess = true;
                break;
            } catch (err) {
                lastError = err;
                console.warn(`Chunk API call to ${url} failed: ${err.message}`);
            }
        }
        
        if (!chunkSuccess) {
            await chrome.storage.local.set({
                apiState: { status: "error", error: lastError?.message || "All endpoints failed on a chunk" }
            });
            return;
        }
    }

    // Mark as completed when done
    await chrome.storage.local.set({
        apiState: { status: "completed", progress: numbers.length, total: numbers.length, error: null }
    });
}