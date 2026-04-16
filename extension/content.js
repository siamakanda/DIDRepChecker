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

// Scroll fallback (keep as before)
async function loadAllNumbersViaScroll() {
    return new Promise(async (resolve) => {
        let previousCount = 0;
        let stableCount = 0;
        let attempts = 0;
        while (attempts < 30) {
            window.scrollTo(0, document.body.scrollHeight);
            await new Promise(r => setTimeout(r, 1500));
            const checkboxes = document.querySelectorAll('input[type="checkbox"][id^="qaSelectedNumber_"]');
            const count = checkboxes.length;
            if (count === previousCount) {
                stableCount++;
                if (stableCount >= 3) break;
            } else {
                stableCount = 0;
                previousCount = count;
            }
            attempts++;
        }
        const checkboxes = document.querySelectorAll('input[type="checkbox"][id^="qaSelectedNumber_"]');
        const numbers = Array.from(checkboxes).map(cb => cb.value).filter(v => v);
        resolve(numbers);
    });
}