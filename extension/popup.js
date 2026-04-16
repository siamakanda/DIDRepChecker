// popup.js – Orchestrates UI, API calls, selection, and statistics

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
const copyResultsBtn = document.getElementById("copyResultsBtn");
const exportResultsBtn = document.getElementById("exportResultsBtn");
const apiUrlsListDiv = document.getElementById("apiUrlsList");
const newApiUrlInput = document.getElementById("newApiUrl");
const addApiUrlBtn = document.getElementById("addApiUrlBtn");
const apiStatus = document.getElementById("apiStatus");
const clearStorageBtn = document.getElementById("clearStorageBtn");
const progressOverlay = document.getElementById("progressOverlay");

// Data
let capturedNumbers = [];
let selectedNumbersToSend = [];
let apiResults = [];
let currentSortField = "total_calls";
let currentSortAsc = true;
let currentFilter = "all";
let lastSelectedCount = 0;

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

function showProgress(show) {
    progressOverlay.style.display = show ? "flex" : "none";
}

function updateStats() {
    document.getElementById("statCaptured").innerText = capturedNumbers.length;
    document.getElementById("statSent").innerText = selectedNumbersToSend.length;
    document.getElementById("statResults").innerText = apiResults.length;
    document.getElementById("statSelectedOnPage").innerText = lastSelectedCount;
}

// Load captured numbers from storage
async function loadCapturedNumbers() {
    numbersContainer.innerHTML = "Loading numbers...";
    try {
        const response = await chrome.runtime.sendMessage({ action: "getCapturedNumbers" });
        capturedNumbers = response.numbers || [];
        if (capturedNumbers.length) {
            renderNumberList();
        } else {
            numbersContainer.innerHTML = '<div class="empty-state">📭 No numbers captured yet. Refresh the Peerless page.</div>';
            selectedNumbersToSend = [];
        }
        updateStats();
    } catch (err) {
        numbersContainer.innerHTML = `<div class="empty-state">⚠️ Error: ${err.message}</div>`;
    }
}

function renderNumberList() {
    selectedNumbersToSend = [...capturedNumbers];
    let html = "";
    capturedNumbers.forEach(num => {
        html += `<div class="number-item">
            <input type="checkbox" class="num-checkbox" value="${num}" checked> <span>${num}</span>
        </div>`;
    });
    numbersContainer.innerHTML = html;
    document.querySelectorAll('.num-checkbox').forEach(cb => {
        cb.addEventListener('change', updateSelectedNumbers);
    });
    updateStats();
}

function updateSelectedNumbers() {
    const checkboxes = document.querySelectorAll('.num-checkbox');
    selectedNumbersToSend = Array.from(checkboxes).filter(cb => cb.checked).map(cb => cb.value);
    updateStats();
}

// API call to reputation server
async function callReputationApi(numbers, description = "numbers") {
    if (!numbers.length) {
        apiStatus.innerText = "No numbers to send.";
        return false;
    }
    showProgress(true);
    apiStatus.innerText = `Checking reputation for ${numbers.length} ${description}...`;
    resultsPlaceholder.style.display = "block";
    resultsContent.style.display = "none";
    try {
        const response = await chrome.runtime.sendMessage({ action: "callReputationApi", numbers: numbers });
        if (response.success) {
            apiResults = response.data;
            await chrome.runtime.sendMessage({ action: "storeApiResults", results: apiResults });
            renderResultsTable();
            resultsPlaceholder.style.display = "none";
            resultsContent.style.display = "block";
            apiStatus.innerText = `✅ Received ${apiResults.length} reputation results.`;
            updateStats();
            return true;
        } else {
            apiStatus.innerText = `❌ API error: ${response.error}`;
            resultsPlaceholder.innerHTML = `<div class="empty-state">❌ API error: ${response.error}</div>`;
            resultsPlaceholder.style.display = "block";
            return false;
        }
    } catch (err) {
        apiStatus.innerText = `❌ Error: ${err.message}`;
        resultsPlaceholder.innerHTML = `<div class="empty-state">❌ ${err.message}</div>`;
        return false;
    } finally {
        showProgress(false);
    }
}

function renderResultsTable() {
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
        row.insertCell(0).innerText = res.phone_number;
        row.insertCell(1).innerText = res.reputation;
        row.insertCell(2).innerText = res.robokiller_status || "";
        row.insertCell(3).innerText = res.total_calls || "0";
        row.insertCell(4).innerText = res.user_reports || "0";
        row.insertCell(5).innerText = res.last_call || "N/A";
    });
    updateStats();
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
            apiStatus.innerText = `✅ Selected ${lastSelectedCount} numbers on page.`;
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

// Event listeners
sendSelectedBtn.addEventListener("click", () => callReputationApi(selectedNumbersToSend, "selected numbers"));
sendTopPageBtn.addEventListener("click", () => {
    let n = parseInt(topNPageInput.value);
    if (isNaN(n) || n <= 0) n = capturedNumbers.length;
    const topNumbers = capturedNumbers.slice(0, n);
    callReputationApi(topNumbers, `top ${n} from page`);
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
    renderResultsTable();
});
sortSelect.addEventListener("change", () => {
    currentSortField = sortSelect.value;
    renderResultsTable();
});
sortAscBtn.addEventListener("click", () => {
    currentSortAsc = true;
    renderResultsTable();
});
sortDescBtn.addEventListener("click", () => {
    currentSortAsc = false;
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
});
copyResultsBtn.addEventListener("click", async () => {
    const numbers = getTopResultsNumbers(999999);
    if (!numbers.length) return;
    try {
        await navigator.clipboard.writeText(numbers.join("\n"));
        apiStatus.innerText = `✅ Copied ${numbers.length} DIDs to clipboard.`;
    } catch (err) {
        apiStatus.innerText = "❌ Copy failed: " + err.message;
    }
});
exportResultsBtn.addEventListener("click", exportResultsCSV);
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
clearStorageBtn.addEventListener("click", async () => {
    await chrome.runtime.sendMessage({ action: "clearStoredData" });
    apiResults = [];
    resultsPlaceholder.style.display = "block";
    resultsContent.style.display = "none";
    apiStatus.innerText = "Stored results cleared.";
    loadCapturedNumbers();
});

// Load stored selected count on start
chrome.storage.local.get(['lastSelectedCount'], (res) => {
    lastSelectedCount = res.lastSelectedCount || 0;
    updateStats();
});

// Initial loads
loadCapturedNumbers();
loadApiUrls();
// Load previously stored API results if any
chrome.runtime.sendMessage({ action: "getApiResults" }, (response) => {
    if (response.results && response.results.length) {
        apiResults = response.results;
        renderResultsTable();
        resultsPlaceholder.style.display = "none";
        resultsContent.style.display = "block";
        updateStats();
    }
});