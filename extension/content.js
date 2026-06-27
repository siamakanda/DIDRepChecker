// content.js – injects inject.js and relays messages

// Inject the script that contains both sniffer and persistent selector
const script = document.createElement('script');
script.src = chrome.runtime.getURL('inject.js');
script.onload = () => script.remove();
(document.head || document.documentElement).appendChild(script);

// Listen for numbers captured by the sniffer
window.addEventListener('NEW_NUMBERS_FOUND', (event) => {
    const numbers = event.detail;
    if (numbers && numbers.length) {
        chrome.runtime.sendMessage({ action: "storeCapturedNumbers", numbers: numbers });
    }
});

// Listen for sniffer fallback — triggered by inject.js when no API calls detected
let fallbackTriggered = false;
window.addEventListener('message', (event) => {
    if (event.source !== window) return;
    if (event.data.type === 'REQUEST_SCROLL_FALLBACK' && !fallbackTriggered) {
        fallbackTriggered = true;
        loadAllNumbersViaScroll().then(numbers => {
            if (numbers.length) {
                chrome.runtime.sendMessage({ action: "storeCapturedNumbers", numbers: numbers });
            }
        });
    }
});

// Listen for selection requests from the popup (via background)
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "selectNumbers") {
        // Forward the numbers to the injected script via postMessage
        window.postMessage({
            type: "UPDATE_SELECTION_NUMBERS",
            numbers: request.numbers
        }, "*");
        sendResponse({ success: true, selected: request.numbers.length });
        return true;
    }
    else if (request.action === "loadAllNumbersViaScroll") {
        // Fallback scroll extraction (if needed)
        loadAllNumbersViaScroll().then(numbers => {
            sendResponse({ numbers });
        });
        return true;
    }
});

// Scroll fallback — extracts checkbox DIDs from the Peerless page
async function loadAllNumbersViaScroll() {
    const maxAttempts = 20;
    const scrollDelay = 300;
    let previousCount = 0;
    let stableCount = 0;
    let lastScrollTop = -1;

    for (let attempt = 0; attempt < maxAttempts; attempt++) {
        const container = document.querySelector('[class*="scroll"]') || document.scrollingElement || document.body;
        container.scrollTo(0, container.scrollHeight);
        await new Promise(r => setTimeout(r, scrollDelay));

        const currentScrollTop = container.scrollTop;
        if (currentScrollTop === lastScrollTop) break; // reached bottom
        lastScrollTop = currentScrollTop;

        const checkboxes = document.querySelectorAll('input[type="checkbox"][id^="qaSelectedNumber_"]');
        const count = checkboxes.length;
        if (count > 0 && count === previousCount) {
            stableCount++;
            if (stableCount >= 2) break;
        } else {
            stableCount = 0;
            previousCount = count;
        }
    }

    const checkboxes = document.querySelectorAll('input[type="checkbox"][id^="qaSelectedNumber_"]');
    return Array.from(checkboxes).map(cb => cb.value).filter(Boolean);
}