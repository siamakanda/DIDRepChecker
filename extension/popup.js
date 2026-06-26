// popup.js – Full version with default Positive filter, auto‑switch to Results, and selection count message

// DOM elements
const numbersContainer = document.getElementById("numbersContainer");
const sendSelectedBtn = document.getElementById("sendSelectedBtn");
const sendTopPageBtn = document.getElementById("sendTopPageBtn");
const topNPageInput = document.getElementById("topNPage");
const selectAllBtn = document.getElementById("selectAllBtn");
const deselectAllBtn = document.getElementById("deselectAllBtn");
const resultsPlaceholder = document.getElementById("resultsPlaceholder");
const resultsContent = document.getElementById("resultsContent");
const filterSelect = document.getElementById("filterSelect");
const sortSelect = document.getElementById("sortSelect");
const sortAscBtn = document.getElementById("sortAscBtn");
const sortDescBtn = document.getElementById("sortDescBtn");
const topNResultsInput = document.getElementById("topNResults");
const selectTopResultsBtn = document.getElementById("selectTopResultsBtn");
const selectCheckedResultsBtn = document.getElementById("selectCheckedResultsBtn");
const copyResultsBtn = document.getElementById("copyResultsBtn");
const exportResultsBtn = document.getElementById("exportResultsBtn");
const apiUrlsListDiv = document.getElementById("apiUrlsList");
const newApiUrlInput = document.getElementById("newApiUrl");
const addApiUrlBtn = document.getElementById("addApiUrlBtn");
const apiStatus = document.getElementById("apiStatus");
const clearStorageBtn = document.getElementById("clearStorageBtn");
const clearResultsBtn = document.getElementById("clearResultsBtn");
const progressOverlay = document.getElementById("progressOverlay");
const selectAllRowsCheckbox = document.getElementById("selectAllRows");

// Paste elements
const showPasteBoxBtn = document.getElementById("showPasteBoxBtn");
const pasteBox = document.getElementById("pasteBox");
const pasteNumbersTextarea = document.getElementById("pasteNumbersTextarea");
const usePastedNumbersBtn = document.getElementById("usePastedNumbersBtn");
const cancelPasteBtn = document.getElementById("cancelPasteBtn");
const resetToCapturedBtn = document.getElementById("resetToCapturedBtn");

// API Key elements
const apiKeyInput = document.getElementById("apiKeyInput");
const saveApiKeyBtn = document.getElementById("saveApiKeyBtn");
const apiKeyStatus = document.getElementById("apiKeyStatus");

function setApiStatusText(text) {
    apiStatus.innerText = text;
    const pt = document.getElementById("progressText");
    if (pt) pt.innerText = text;
}

// Data
let capturedNumbers = [];
let selectedNumbersToSend = [];
let apiResults = [];
let currentSortField = "total_calls";
let currentSortAsc = true;
let currentFilter = "Positive";   // ✅ Default to Positive
let lastSelectedCount = 0;
let lastSentCount = 0;
let originalCapturedNumbers = [];

// Helper: Clean phone number
function cleanNumberSimple(input) {
    if (!input) return "";
    let cleaned = input.toString().replace(/\D/g, "");
    if (cleaned.startsWith("1") && cleaned.length === 11) cleaned = cleaned.slice(1);
    return cleaned.length === 10 ? cleaned : "";
}

function parsePastedNumbers(text) {
    const parts = text.split(/[\n, ]+/);
    const numbers = [];
    for (let part of parts) {
        const cleaned = cleanNumberSimple(part);
        if (cleaned) numbers.push(cleaned);
    }
    return [...new Set(numbers)];
}

// ---------- Persistence Keys ----------
const PREF_KEYS = {
    filter: "pref_filter",
    sortField: "pref_sortField",
    sortAsc: "pref_sortAsc",
    topNPage: "pref_topNPage",
    topNResults: "pref_topNResults"
};

async function savePreferences() {
    const prefs = {
        [PREF_KEYS.filter]: filterSelect.value,
        [PREF_KEYS.sortField]: sortSelect.value,
        [PREF_KEYS.sortAsc]: currentSortAsc,
        [PREF_KEYS.topNPage]: topNPageInput.value,
        [PREF_KEYS.topNResults]: topNResultsInput.value
    };
    await chrome.storage.local.set(prefs);
}

async function loadPreferences() {
    const prefs = await chrome.storage.local.get(Object.values(PREF_KEYS));
    if (prefs[PREF_KEYS.filter]) {
        filterSelect.value = prefs[PREF_KEYS.filter];
        currentFilter = filterSelect.value;
    } else {
        // No saved filter – set to Positive
        filterSelect.value = "Positive";
        currentFilter = "Positive";
    }
    if (prefs[PREF_KEYS.sortField]) sortSelect.value = prefs[PREF_KEYS.sortField];
    if (typeof prefs[PREF_KEYS.sortAsc] === 'boolean') currentSortAsc = prefs[PREF_KEYS.sortAsc];
    if (prefs[PREF_KEYS.topNPage]) topNPageInput.value = prefs[PREF_KEYS.topNPage];
    if (prefs[PREF_KEYS.topNResults]) topNResultsInput.value = prefs[PREF_KEYS.topNResults];
    currentSortField = sortSelect.value;
    renderResultsTable();
}

// Tabs
const tabs = document.querySelectorAll(".tab");
const panels = {
    numbers: document.getElementById("numbersPanel"),
    results: document.getElementById("resultsPanel"),
    settings: document.getElementById("settingsPanel")
};
tabs.forEach(tab => {
    tab.addEventListener("click", () => {
        const target = tab.dataset.tab;
        tabs.forEach(t => t.classList.remove("active"));
        tab.classList.add("active");
        Object.values(panels).forEach(p => p.classList.remove("active-panel"));
        panels[target].classList.add("active-panel");
    });
});

function switchToResultsTab() {
    const resultsTab = document.querySelector('.tab[data-tab="results"]');
    if (resultsTab && !resultsTab.classList.contains("active")) {
        resultsTab.click();
    }
}

function showProgress(show) {
    progressOverlay.style.display = show ? "flex" : "none";
}

function updateStats() {
    document.getElementById("statCaptured").innerText = capturedNumbers.length;
    document.getElementById("statSent").innerText = lastSentCount;

    // Color-coded: total with positive(green) / negative(red) breakdown
    var pos = 0, neg = 0;
    for (var i = 0; i < apiResults.length; i++) {
        if (apiResults[i].reputation === "Positive") pos++;
        else if (apiResults[i].reputation === "Negative") neg++;
    }
    var statResults = document.getElementById("statResults");
    if (pos + neg > 0) {
        statResults.innerHTML = apiResults.length + ' <span style="font-size:11px;color:var(--success)">' + pos + '</span> <span style="font-size:11px;color:var(--danger)">' + neg + '</span>';
    } else {
        statResults.innerText = apiResults.length;
    }
    document.getElementById("statSelectedOnPage").innerText = lastSelectedCount;
}

// Clear API results
async function clearApiResults() {
    apiResults = [];
    lastSentCount = 0;
    await chrome.runtime.sendMessage({ action: "storeApiResults", results: [] });
    resultsPlaceholder.style.display = "block";
    resultsContent.style.display = "none";
    apiStatus.innerText = "Results cleared.";
    updateStats();
    updateFilterDropdown();
    renderResultsTable();
}

// Load captured numbers from storage
async function loadCapturedNumbers() {
    numbersContainer.innerHTML = "Loading numbers...";
    try {
        const response = await chrome.runtime.sendMessage({ action: "getCapturedNumbers" });
        const newNumbers = response.numbers || [];
        originalCapturedNumbers = [...newNumbers];
        if (JSON.stringify(capturedNumbers) !== JSON.stringify(newNumbers)) {
            await clearApiResults();
            lastSelectedCount = 0;
            await chrome.storage.local.set({ lastSelectedCount: 0 });
        }
        capturedNumbers = newNumbers;
        if (capturedNumbers.length) {
            renderNumberList();
            resetToCapturedBtn.style.display = "none";
            showPasteBoxBtn.style.display = "inline-flex";
        } else {
            numbersContainer.innerHTML = '<div class="empty-state">📭 No numbers captured yet. Refresh the Peerless page or paste numbers.</div>';
            selectedNumbersToSend = [];
        }
        updateStats();
    } catch (err) {
        numbersContainer.innerHTML = `<div class="empty-state">⚠️ Error: ${err.message}</div>`;
    }
}

function renderNumberList() {
    selectedNumbersToSend = [...capturedNumbers];
    var searchText = (document.getElementById("numberSearch")?.value || "").trim().toLowerCase();
    var filtered = searchText ? capturedNumbers.filter(function(n) { return n.indexOf(searchText) >= 0; }) : capturedNumbers;
    var html = "";
    filtered.forEach(function(num) {
        html += '<div class="number-item"><input type="checkbox" class="num-checkbox" value="' + num + '" checked> <span>' + num + '</span></div>';
    });
    numbersContainer.innerHTML = html || '<div class="empty-state">No numbers match your search</div>';
    document.querySelectorAll('.num-checkbox').forEach(function(cb) {
        cb.addEventListener('change', updateSelectedNumbers);
    });
    updateStats();
    updateNumberCount();
}

function updateNumberCount() {
    var label = document.getElementById("numberCountLabel");
    if (label) label.textContent = capturedNumbers.length;
}

function updateSelectedNumbers() {
    const checkboxes = document.querySelectorAll('.num-checkbox');
    selectedNumbersToSend = Array.from(checkboxes).filter(cb => cb.checked).map(cb => cb.value);
    updateStats();
}

// API call to reputation server (background handles chunking)
async function callReputationApi(numbers, description = "numbers") {
    if (!numbers.length) {
        apiStatus.innerText = "No numbers to send.";
        return false;
    }
    lastSentCount = numbers.length;
    showProgress(true);
    apiStatus.innerText = `Checking reputation for ${numbers.length} ${description}...`;
    resultsPlaceholder.style.display = "block";
    resultsContent.style.display = "none";
    try {
        await chrome.runtime.sendMessage({ action: "startReputationCheck", numbers: numbers });
    } catch (err) {
        apiStatus.innerText = `❌ Error: ${err.message}`;
        resultsPlaceholder.innerHTML = `<div class="empty-state">❌ ${err.message}</div>`;
        showProgress(false);
        return false;
    }
}

function updateFilterDropdown() {
    if (!apiResults.length) {
        filterSelect.innerHTML = `<option value="all">All (0)</option>
                                  <option value="Positive">✅ Positive (0)</option>
                                  <option value="Negative">❌ Negative (0)</option>
                                  <option value="Neutral">🟡 Neutral / Not Found (0)</option>
                                  <option value="Blocked">🚫 Blocked / Error (0)</option>`;
        return;
    }
    const positiveCount = apiResults.filter(r => r.reputation === 'Positive').length;
    const negativeCount = apiResults.filter(r => r.reputation === 'Negative').length;
    const neutralCount = apiResults.filter(r => ['Neutral', 'Not Found', 'No Data Available'].includes(r.reputation)).length;
    const blockedCount = apiResults.filter(r => ['Blocked', 'Error', 'Parse Error', 'HTTP'].some(e => r.reputation.includes(e))).length;
    const allCount = apiResults.length;

    const currentValue = filterSelect.value;
    filterSelect.innerHTML = `
        <option value="all">All (${allCount})</option>
        <option value="Positive">✅ Positive (${positiveCount})</option>
        <option value="Negative">❌ Negative (${negativeCount})</option>
        <option value="Neutral">🟡 Neutral / Not Found (${neutralCount})</option>
        <option value="Blocked">🚫 Blocked / Error (${blockedCount})</option>
    `;
    filterSelect.value = currentValue;
}

function renderResultsTable() {
    if (!apiResults.length) {
        document.getElementById("resultsBody").innerHTML = '<tr><td colspan="7" class="empty-state">No results to display. </td> </table>';
        document.getElementById("displayedCount").innerText = "0";
        document.getElementById("totalResultCount").innerText = "0";
        if (selectAllRowsCheckbox) selectAllRowsCheckbox.checked = false;
        return;
    }

    let filtered = [...apiResults];
    if (currentFilter !== "all") {
        filtered = filtered.filter(r => r.reputation === currentFilter);
    }
    filtered.sort((a,b) => {
        let aVal = a[currentSortField];
        let bVal = b[currentSortField];
        if (currentSortField === "total_calls" || currentSortField === "user_reports") {
            aVal = parseInt(aVal) || 0;
            bVal = parseInt(bVal) || 0;
        }
        if (aVal < bVal) return currentSortAsc ? -1 : 1;
        if (aVal > bVal) return currentSortAsc ? 1 : -1;
        return 0;
    });

    const tbody = document.getElementById("resultsBody");
    tbody.innerHTML = "";
    filtered.forEach(res => {
        const row = tbody.insertRow();
        const cbCell = row.insertCell(0);
        const cb = document.createElement("input");
        cb.type = "checkbox";
        cb.className = "row-checkbox";
        cb.dataset.number = res.phone_number;
        cbCell.appendChild(cb);
        row.insertCell(1).innerText = res.phone_number;
        row.insertCell(2).innerHTML = getReputationBadge(res.reputation);
        row.insertCell(3).innerText = res.robokiller_status || "";
        row.insertCell(4).innerText = res.total_calls || "0";
        row.insertCell(5).innerText = res.user_reports || "0";
        row.insertCell(6).innerText = res.last_call || "N/A";
    });

    document.getElementById("displayedCount").innerText = filtered.length;
    document.getElementById("totalResultCount").innerText = apiResults.length;
    updateStats();

    const allCheckboxes = document.querySelectorAll('.row-checkbox');
    const checkedBoxes = document.querySelectorAll('.row-checkbox:checked');
    if (selectAllRowsCheckbox) {
        selectAllRowsCheckbox.checked = allCheckboxes.length > 0 && checkedBoxes.length === allCheckboxes.length;
        selectAllRowsCheckbox.indeterminate = checkedBoxes.length > 0 && checkedBoxes.length < allCheckboxes.length;
    }
}

function getTopResultsNumbers(n) {
    let filtered = [...apiResults];
    if (currentFilter !== "all") {
        filtered = filtered.filter(r => r.reputation === currentFilter);
    }
    filtered.sort((a,b) => {
        let aVal = a[currentSortField];
        let bVal = b[currentSortField];
        if (currentSortField === "total_calls" || currentSortField === "user_reports") {
            aVal = parseInt(aVal) || 0;
            bVal = parseInt(bVal) || 0;
        }
        if (aVal < bVal) return currentSortAsc ? -1 : 1;
        if (aVal > bVal) return currentSortAsc ? 1 : -1;
        return 0;
    });
    return filtered.slice(0, n).map(r => r.phone_number);
}

function getCheckedNumbersFromResults() {
    const checkboxes = document.querySelectorAll('.row-checkbox:checked');
    return Array.from(checkboxes).map(cb => cb.dataset.number);
}

async function selectNumbersOnPage(numbers) {
    if (!numbers.length) return;
    showProgress(true);
    apiStatus.innerText = `Selecting ${numbers.length} numbers on Peerless page...`;
    try {
        const response = await chrome.runtime.sendMessage({ action: "selectNumbersOnPage", numbers: numbers });
        if (response && response.success) {
            lastSelectedCount = response.selected;
            await chrome.storage.local.set({ lastSelectedCount: lastSelectedCount });
            updateStats();
            // ✅ Show explicit selection count
            apiStatus.innerText = `✅ Selected ${lastSelectedCount} numbers on Peerless page.`;
        } else {
            apiStatus.innerText = `❌ Selection error: ${response?.error || "unknown"}`;
        }
    } catch (err) {
        apiStatus.innerText = `❌ Selection error: ${err.message}`;
    } finally {
        showProgress(false);
    }
}

// API URLs management
async function loadApiUrls() {
    const response = await chrome.runtime.sendMessage({ action: "getApiUrls" });
    renderApiUrls(response.urls);
}

function renderApiUrls(urls) {
    apiUrlsListDiv.innerHTML = "";
    if (!urls.length) {
        apiUrlsListDiv.innerHTML = '<div class="empty-state">No endpoints configured. Add one below.</div>';
        return;
    }
    urls.forEach((url, idx) => {
        const div = document.createElement("div");
        div.className = "api-url-item";
        div.innerHTML = `
            <input type="text" value="${url}" data-idx="${idx}" class="api-url-input">
            <button class="remove-url" data-idx="${idx}" style="background:#dc3545; color:white; border:none; border-radius:4px; cursor:pointer;">❌</button>
        `;
        apiUrlsListDiv.appendChild(div);
    });
    document.querySelectorAll('.remove-url').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const idx = parseInt(btn.dataset.idx);
            const newUrls = [...urls];
            newUrls.splice(idx, 1);
            await chrome.runtime.sendMessage({ action: "saveApiUrls", urls: newUrls });
            renderApiUrls(newUrls);
        });
    });
    document.querySelectorAll('.api-url-input').forEach(input => {
        input.addEventListener('change', async (e) => {
            const idx = parseInt(input.dataset.idx);
            const newUrls = [...urls];
            newUrls[idx] = input.value;
            await chrome.runtime.sendMessage({ action: "saveApiUrls", urls: newUrls });
        });
    });
}

function exportResultsCSV() {
    if (!apiResults.length) {
        apiStatus.innerText = "No results to export.";
        return;
    }
    const headers = ["phone_number","reputation","robokiller_status","total_calls","user_reports","last_call","scraped_at"];
    const rows = apiResults.map(r => headers.map(h => r[h] || "").join(","));
    const csv = [headers.join(","), ...rows].join("\n");
    const blob = new Blob([csv], {type: "text/csv"});
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `did_results_${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    apiStatus.innerText = "CSV exported.";
}

// ---------- Paste Numbers Logic ----------
showPasteBoxBtn.addEventListener("click", () => {
    pasteBox.style.display = "block";
    showPasteBoxBtn.style.display = "none";
    pasteNumbersTextarea.value = "";
});
cancelPasteBtn.addEventListener("click", () => {
    pasteBox.style.display = "none";
    showPasteBoxBtn.style.display = "inline-flex";
});
usePastedNumbersBtn.addEventListener("click", () => {
    const raw = pasteNumbersTextarea.value;
    if (!raw.trim()) {
        apiStatus.innerText = "No numbers entered.";
        return;
    }
    const numbers = parsePastedNumbers(raw);
    if (numbers.length === 0) {
        apiStatus.innerText = "No valid phone numbers found.";
        return;
    }
    capturedNumbers = numbers;
    selectedNumbersToSend = [...capturedNumbers];
    renderNumberList();
    updateStats();
    chrome.storage.local.set({ capturedNumbers: capturedNumbers });
    apiStatus.innerText = `✅ Loaded ${numbers.length} pasted numbers.`;
    pasteBox.style.display = "none";
    showPasteBoxBtn.style.display = "none";
    resetToCapturedBtn.style.display = "inline-flex";
});
resetToCapturedBtn.addEventListener("click", async () => {
    capturedNumbers = [...originalCapturedNumbers];
    selectedNumbersToSend = [...capturedNumbers];
    renderNumberList();
    updateStats();
    apiStatus.innerText = `↻ Reset to ${capturedNumbers.length} auto-captured numbers.`;
    resetToCapturedBtn.style.display = "none";
    showPasteBoxBtn.style.display = "inline-flex";
    chrome.storage.local.set({ capturedNumbers: capturedNumbers });
});

// Live paste counter
var pasteTextarea = document.getElementById("pasteNumbersTextarea");
if (pasteTextarea) {
    pasteTextarea.addEventListener("input", function() {
        var count = parsePastedNumbers(pasteTextarea.value).length;
        var pc = document.getElementById("pasteCount");
        if (pc) pc.textContent = count + " numbers detected";
    });
}

// Search filter
var searchInput = document.getElementById("numberSearch");
if (searchInput) {
    searchInput.addEventListener("input", function() { renderNumberList(); });
}

// ---------- Event Listeners ----------
sendSelectedBtn.addEventListener("click", () => callReputationApi(selectedNumbersToSend, "selected numbers"));
sendTopPageBtn.addEventListener("click", () => {
    let n = parseInt(topNPageInput.value);
    if (isNaN(n) || n <= 0) n = capturedNumbers.length;
    const topNumbers = capturedNumbers.slice(0, n);
    callReputationApi(topNumbers, `top ${n} from page`);
    savePreferences();
});
selectAllBtn.addEventListener("click", () => {
    document.querySelectorAll('.num-checkbox').forEach(cb => { cb.checked = true; });
    updateSelectedNumbers();
});
deselectAllBtn.addEventListener("click", () => {
    document.querySelectorAll('.num-checkbox').forEach(cb => { cb.checked = false; });
    updateSelectedNumbers();
});
filterSelect.addEventListener("change", () => {
    currentFilter = filterSelect.value;
    savePreferences();
    renderResultsTable();
});
sortSelect.addEventListener("change", () => {
    currentSortField = sortSelect.value;
    savePreferences();
    renderResultsTable();
});
sortAscBtn.addEventListener("click", () => {
    currentSortAsc = true;
    sortAscBtn.classList.add("sort-active");
    sortDescBtn.classList.remove("sort-active");
    savePreferences();
    renderResultsTable();
});
sortDescBtn.addEventListener("click", () => {
    currentSortAsc = false;
    sortDescBtn.classList.add("sort-active");
    sortAscBtn.classList.remove("sort-active");
    savePreferences();
    renderResultsTable();
});
selectTopResultsBtn.addEventListener("click", () => {
    if (!apiResults.length) {
        apiStatus.innerText = "No reputation results to select from.";
        return;
    }
    let n = parseInt(topNResultsInput.value);
    if (isNaN(n) || n <= 0) n = apiResults.length;
    const numbers = getTopResultsNumbers(n);
    selectNumbersOnPage(numbers);
    savePreferences();
});
selectCheckedResultsBtn.addEventListener("click", () => {
    const numbers = getCheckedNumbersFromResults();
    if (numbers.length) {
        selectNumbersOnPage(numbers);
    } else {
        apiStatus.innerText = "No rows checked in results table.";
    }
});
copyResultsBtn.addEventListener("click", async () => {
    const numbers = getTopResultsNumbers(999999);
    if (!numbers.length) return;
    await navigator.clipboard.writeText(numbers.join("\n"));
    apiStatus.innerText = `✅ Copied ${numbers.length} DIDs to clipboard.`;
});
exportResultsBtn.addEventListener("click", exportResultsCSV);
topNPageInput.addEventListener("change", savePreferences);
topNResultsInput.addEventListener("change", savePreferences);

if (selectAllRowsCheckbox) {
    selectAllRowsCheckbox.addEventListener("change", (e) => {
        const isChecked = e.target.checked;
        document.querySelectorAll('.row-checkbox').forEach(cb => cb.checked = isChecked);
    });
}

addApiUrlBtn.addEventListener("click", async () => {
    let newUrl = newApiUrlInput.value.trim();
    if (!newUrl) return;
    const response = await chrome.runtime.sendMessage({ action: "getApiUrls" });
    const urls = response.urls;
    if (!urls.includes(newUrl)) {
        urls.push(newUrl);
        await chrome.runtime.sendMessage({ action: "saveApiUrls", urls: urls });
        renderApiUrls(urls);
        newApiUrlInput.value = "";
        apiStatus.innerText = "✅ Endpoint added.";
    } else {
        apiStatus.innerText = "URL already exists.";
    }
});

// API Key save
if (saveApiKeyBtn) {
    saveApiKeyBtn.addEventListener("click", async () => {
        const key = apiKeyInput ? apiKeyInput.value.trim() : "";
        await chrome.runtime.sendMessage({ action: "saveApiKey", key: key });
        if (apiKeyStatus) {
            apiKeyStatus.innerText = key ? "✅ API key saved." : "✅ API key cleared (auth disabled).";
            apiKeyStatus.style.color = "var(--success)";
            setTimeout(() => { if (apiKeyStatus) apiKeyStatus.innerText = ""; }, 3000);
        }
    });
}

clearStorageBtn.addEventListener("click", async () => {
    await chrome.runtime.sendMessage({ action: "clearStoredData" });
    apiResults = [];
    lastSentCount = 0;
    lastSelectedCount = 0;
    await chrome.storage.local.set({ lastSelectedCount: 0 });
    resultsPlaceholder.style.display = "block";
    resultsContent.style.display = "none";
    apiStatus.innerText = "Stored results cleared.";
    loadCapturedNumbers();
});
if (clearResultsBtn) {
    clearResultsBtn.addEventListener("click", clearApiResults);
}

// Storage listener for state and results
chrome.storage.onChanged.addListener((changes, namespace) => {
    if (namespace === 'local') {
        if (changes.apiState) {
            const state = changes.apiState.newValue;
            if (state) {
                if (state.status === "running") {
                    showProgress(true);
                    if (state.total) {
                        setApiStatusText(`Checking reputation... (${state.progress} / ${state.total})`);
                    } else {
                        setApiStatusText("Checking reputation (continued in background)...");
                    }
                } else if (state.status === "completed") {
                    showProgress(false);
                    const count = apiResults.length;
                    setApiStatusText(`✅ Checked ${count} numbers.`);
                } else if (state.status === "error") {
                    showProgress(false);
                    setApiStatusText(`❌ API error: ${state.error}`);
                    resultsPlaceholder.innerHTML = `<div class="empty-state">❌ API error: ${state.error}</div>`;
                    resultsPlaceholder.style.display = "block";
                    resultsContent.style.display = "none";
                }
            }
        }
        if (changes.apiResults) {
            apiResults = changes.apiResults.newValue || [];
            if (apiResults.length > 0) {
                // Ensure filter is set to Positive if no user preference yet
                if (currentFilter === "all" || !filterSelect.value) {
                    filterSelect.value = "Positive";
                    currentFilter = "Positive";
                }
                updateFilterDropdown();
                renderResultsTable();
                resultsPlaceholder.style.display = "none";
                resultsContent.style.display = "block";
                updateStats();
                switchToResultsTab();
            }
        }
    }
});

// Load stored selected count and apiState
chrome.storage.local.get(['lastSelectedCount', 'apiState'], (res) => {
    lastSelectedCount = res.lastSelectedCount || 0;
    if (res.apiState && res.apiState.status === "running") {
        showProgress(true);
        if (res.apiState.total) {
            setApiStatusText(`Checking reputation... (${res.apiState.progress} / ${res.apiState.total})`);
        } else {
            setApiStatusText("Checking reputation (continued in background)...");
        }
    }
    updateStats();
});

// Dark Mode Logic
const darkModeToggle = document.getElementById("darkModeToggle");
chrome.storage.local.get(['darkMode'], (res) => {
    if (res.darkMode) {
        document.body.classList.add('dark-theme');
        if (darkModeToggle) darkModeToggle.checked = true;
    }
});
if (darkModeToggle) {
    darkModeToggle.addEventListener('change', (e) => {
        if (e.target.checked) {
            document.body.classList.add('dark-theme');
            chrome.storage.local.set({ darkMode: true });
        } else {
            document.body.classList.remove('dark-theme');
            chrome.storage.local.set({ darkMode: false });
        }
    });
}

// API Key — load saved key into input field
chrome.runtime.sendMessage({ action: "getApiKey" }, (response) => {
    if (response && response.key && apiKeyInput) {
        apiKeyInput.value = response.key;
    }
});

// Initial loads
loadPreferences();
// Highlight default sort button
if (sortAscBtn && currentSortAsc) sortAscBtn.classList.add("sort-active");
if (sortDescBtn && !currentSortAsc) sortDescBtn.classList.add("sort-active");
loadCapturedNumbers();
loadApiUrls();
chrome.runtime.sendMessage({ action: "getApiResults" }, (response) => {
    if (response.results && response.results.length) {
        apiResults = response.results;
        // Force Positive filter if none saved
        if (currentFilter === "all" || !filterSelect.value) {
            filterSelect.value = "Positive";
            currentFilter = "Positive";
        }
        updateFilterDropdown();
        renderResultsTable();
        resultsPlaceholder.style.display = "none";
        resultsContent.style.display = "block";
        updateStats();
        switchToResultsTab();
        setApiStatusText(`✅ Loaded ${apiResults.length} results from storage.`);
    }
});

// Retry Errors Button Logic
const retryErrorsBtn = document.getElementById("retryErrorsBtn");
if (retryErrorsBtn) {
    retryErrorsBtn.addEventListener("click", () => {
        if (!apiResults || apiResults.length === 0) return;
        const errorKeywords = ['Error', 'Timeout', 'Blocked', 'HTTP', 'Parse Error'];
        const failedNumbers = apiResults
            .filter(r => errorKeywords.some(err => r.reputation && r.reputation.includes(err)))
            .map(r => r.phone_number);
        if (failedNumbers.length === 0) {
            setApiStatusText("No failed numbers found to retry.");
            return;
        }
        setApiStatusText(`Retrying ${failedNumbers.length} failed numbers...`);
        showProgress(true);
        chrome.runtime.sendMessage({ action: "startReputationCheck", numbers: failedNumbers, append: true });
    });
}

// ─── NEW: Reputation badge helper ───────────────────────────────────
function getReputationBadge(rep) {
    if (rep === "Positive") return '<span class="badge badge-positive">Positive</span>';
    if (rep === "Negative") return '<span class="badge badge-negative">Negative</span>';
    if (rep && (rep.includes("Block") || rep.includes("Error") || rep.includes("HTTP") || rep.includes("Timeout")))
        return '<span class="badge badge-error">' + rep + '</span>';
    return '<span class="badge badge-neutral">' + (rep || "Unknown") + '</span>';
}

// ─── NEW: Toast notifications ──────────────────────────────────────
function showToast(msg, type) {
    var container = document.getElementById("toastContainer");
    if (!container) {
        container = document.createElement("div");
        container.id = "toastContainer";
        container.className = "toast-container";
        document.body.appendChild(container);
    }
    var el = document.createElement("div");
    el.className = "toast toast-" + (type || "info");
    el.textContent = msg;
    container.appendChild(el);
    setTimeout(function() { el.style.opacity = "0"; el.style.transition = "opacity .2s"; setTimeout(function() { el.remove(); }, 200); }, 2500);
}

// ─── NEW: Progress bar injection ───────────────────────────────────
function injectProgressBar() {
    if (document.getElementById("progressBarWrap")) return;
    var spinner = document.querySelector(".progress-overlay .spinner");
    if (!spinner) return;
    var wrap = document.createElement("div");
    wrap.id = "progressBarWrap";
    wrap.className = "progress-bar-wrap";
    wrap.innerHTML = '<div id="progressBarFill" class="progress-bar-fill"></div>';
    spinner.appendChild(wrap);
}
function updateProgressBar(pct) {
    injectProgressBar();
    var fill = document.getElementById("progressBarFill");
    if (fill) fill.style.width = Math.min(100, Math.max(0, pct || 0)) + "%";
}

// ─── NEW: Enhanced progress with bar ───────────────────────────────
var origShowProgress = showProgress;
showProgress = function(show) {
    origShowProgress(show);
    if (show) injectProgressBar();
};

var origSetApiStatusText = setApiStatusText;
setApiStatusText = function(text) {
    origSetApiStatusText(text);
    var m = text.match(/\((\d+)\s*\/\s*(\d+)\)/);
    if (m) updateProgressBar(parseInt(m[1]) / parseInt(m[2]) * 100);
    if (text && text.includes("Checked")) updateProgressBar(100);
};

// ─── NEW: Keyboard shortcut Ctrl+Enter ─────────────────────────────
document.addEventListener("keydown", function(e) {
    if (e.ctrlKey && e.key === "Enter") {
        var numbersPanel = document.getElementById("numbersPanel");
        if (numbersPanel && numbersPanel.classList.contains("active-panel")) {
            var sendBtn = document.getElementById("sendSelectedBtn");
            if (sendBtn) sendBtn.click();
        }
    }
});

// ─── NEW: Auto-refresh when new numbers captured ───────────────────
chrome.storage.onChanged.addListener(function(changes, ns) {
    if (ns !== "local") return;
    if (changes.capturedNumbers && changes.capturedNumbers.newValue) {
        var newNums = changes.capturedNumbers.newValue;
        if (newNums.length && JSON.stringify(newNums) !== JSON.stringify(capturedNumbers)) {
            capturedNumbers = newNums;
            originalCapturedNumbers = newNums.slice();
            selectedNumbersToSend = newNums.slice();
            renderNumberList();
            updateStats();
            showToast("Captured " + newNums.length + " numbers", "success");
        }
    }
});