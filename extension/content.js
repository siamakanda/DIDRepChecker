// content.js - Extracts numbers, selects checkboxes, auto-select on scroll

let lastSelectedNumbers = []; // stored list for auto-selection

// Listen for messages from background/popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "extractNumbers") {
    const checkboxes = document.querySelectorAll('input[type="checkbox"][id^="qaSelectedNumber_"]');
    const numbers = Array.from(checkboxes).map(cb => cb.value).filter(v => v && v.length > 0);
    sendResponse({ numbers: numbers });
    return true;
  }
  else if (request.action === "selectNumbers") {
    const numbersToSelect = request.numbers;
    lastSelectedNumbers = numbersToSelect; // store for auto-select
    selectCheckboxes(numbersToSelect);
    sendResponse({ success: true, selected: numbersToSelect.length });
    return true;
  }
});

// Function to click checkboxes that match given numbers
function selectCheckboxes(numbers) {
  const checkboxes = document.querySelectorAll('input[type="checkbox"][id^="qaSelectedNumber_"]');
  checkboxes.forEach(cb => {
    const shouldSelect = numbers.includes(cb.value);
    if (shouldSelect && !cb.checked) {
      cb.click();
      console.log("Selected: " + cb.value);
    } else if (!shouldSelect && cb.checked) {
      // Optionally uncheck? Not needed for our use case, but we can.
      // We'll keep as is.
    }
  });
}

// MutationObserver to auto-select newly added checkboxes that match lastSelectedNumbers
const observer = new MutationObserver((mutations) => {
  if (lastSelectedNumbers.length === 0) return;
  // Look for newly added checkboxes
  mutations.forEach(mutation => {
    mutation.addedNodes.forEach(node => {
      if (node.nodeType === Node.ELEMENT_NODE) {
        const checkboxes = node.querySelectorAll ? node.querySelectorAll('input[type="checkbox"][id^="qaSelectedNumber_"]') : [];
        checkboxes.forEach(cb => {
          if (lastSelectedNumbers.includes(cb.value) && !cb.checked) {
            cb.click();
            console.log("Auto-selected: " + cb.value);
          }
        });
      }
    });
  });
});

// Start observing the whole document for added nodes
observer.observe(document.body, { childList: true, subtree: true });

console.log("DID Reputation Selector content script loaded.");