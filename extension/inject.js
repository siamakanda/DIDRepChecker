// inject.js – intercepts API calls and also provides persistent number selector

(function() {
    // ---------- API Sniffer (unchanged) ----------
    function extractNumbers(data) {
        if (data && data.data && Array.isArray(data.data)) {
            return data.data.map(item => item.number).filter(n => n);
        }
        return [];
    }

    function dispatchNumbers(numbers) {
        if (numbers && numbers.length) {
            window.dispatchEvent(new CustomEvent('NEW_NUMBERS_FOUND', { detail: numbers }));
        }
    }

    const originalOpen = XMLHttpRequest.prototype.open;
    XMLHttpRequest.prototype.open = function(method, url) {
        this.addEventListener('load', function() {
            if (url && url.includes('/api/number')) {
                try {
                    const data = JSON.parse(this.responseText);
                    const numbers = extractNumbers(data);
                    dispatchNumbers(numbers);
                } catch (e) {}
            }
        });
        originalOpen.apply(this, arguments);
    };

    const originalFetch = window.fetch;
    window.fetch = async function(...args) {
        const response = await originalFetch.apply(this, args);
        const url = args[0];
        if (typeof url === 'string' && url.includes('/api/number')) {
            const clone = response.clone();
            const data = await clone.json();
            const numbers = extractNumbers(data);
            dispatchNumbers(numbers);
        }
        return response;
    };

    // ---------- Persistent Number Selector (mimics sample extension) ----------
    let targetNumbers = [];

    // Function to select visible checkboxes that match targetNumbers
    function selectVisibleNumbers() {
        const checkboxes = document.querySelectorAll('input[type="checkbox"][id^="qaSelectedNumber_"]');
        checkboxes.forEach(cb => {
            if (targetNumbers.includes(cb.value) && !cb.checked) {
                cb.click();
            }
        });
    }

    // Run immediately when targetNumbers is updated
    function updateTargetNumbers(newNumbers) {
        targetNumbers = newNumbers;
        selectVisibleNumbers(); // click currently visible ones
    }

    // Set up a MutationObserver to re-run on any DOM changes
    const observer = new MutationObserver(() => {
        selectVisibleNumbers();
    });
    observer.observe(document.body, { childList: true, subtree: true });

    // Also run periodically (every 500ms) to catch any missed due to virtual scrolling
    setInterval(() => {
        selectVisibleNumbers();
    }, 500);

    // Listen for messages from the extension (popup) to update the target numbers
    window.addEventListener('message', (event) => {
        if (event.source !== window) return;
        if (event.data.type === 'UPDATE_SELECTION_NUMBERS') {
            updateTargetNumbers(event.data.numbers);
        }
    });
})();