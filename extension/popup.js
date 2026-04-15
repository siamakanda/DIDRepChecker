// popup.js

let allPageNumbers = [];        // all numbers from page
let selectedNumbersToSend = []; // currently checked numbers in popup list
let apiResults = [];            // raw results from API
let currentSortField = "total_calls";
let currentSortAsc = true;
let currentFilter = "all";

// DOM elements
const numbersContainer = document.getElementById("numbersContainer");
const sendSelectedBtn = document.getElementById("sendSelectedBtn");
const sendTopPageBtn = document.getElementById("sendTopPageBtn");
const topNPageInput = document.getElementById("topNPage");
const resultsSection = document.getElementById("resultsSection");
const filterSelect = document.getElementById("filterSelect");
const sortSelect = document.getElementById("sortSelect");
const sortAscBtn = document.getElementById("sortAscBtn");
const sortDescBtn = document.getElementById("sortDescBtn");
const topNResultsInput = document.getElementById("topNResults");
const selectTopResultsBtn = document.getElementById("selectTopResultsBtn");
const copyResultsBtn = document.getElementById("copyResultsBtn");
const apiUrlsListDiv = document.getElementById("apiUrlsList");
const newApiUrlInput = document.getElementById("newApiUrl");
const addApiUrlBtn = document.getElementById("addApiUrlBtn");
const apiStatus = document.getElementById("apiStatus");

// Load page numbers on popup open
async function loadPageNumbers() {
  numbersContainer.innerHTML = "Loading numbers from page...";
  try {
    const response = await chrome.runtime.sendMessage({ action: "getNumbersFromPage" });
    if (response && response.numbers) {
      allPageNumbers = response.numbers;
      renderNumberList();
    } else {
      numbersContainer.innerHTML = "No numbers found on page. " + (response?.error || "");
    }
  } catch (err) {
    numbersContainer.innerHTML = "Error: " + err.message;
  }
}

// Render list of numbers with checkboxes (all checked by default)
function renderNumberList() {
  if (!allPageNumbers.length) {
    numbersContainer.innerHTML = "No phone numbers found on page.";
    return;
  }
  selectedNumbersToSend = [...allPageNumbers]; // default all selected
  let html = "";
  allPageNumbers.forEach(num => {
    html += `<div class="number-item">
      <input type="checkbox" class="num-checkbox" value="${num}" checked> <span>${num}</span>
    </div>`;
  });
  numbersContainer.innerHTML = html;
  // attach event listeners to update selectedNumbersToSend
  document.querySelectorAll('.num-checkbox').forEach(cb => {
    cb.addEventListener('change', updateSelectedNumbers);
  });
}

function updateSelectedNumbers() {
  const checkboxes = document.querySelectorAll('.num-checkbox');
  selectedNumbersToSend = Array.from(checkboxes).filter(cb => cb.checked).map(cb => cb.value);
}

// API call via background
async function callApi(numbers) {
  apiStatus.innerText = "Calling API...";
  resultsSection.style.display = "none";
  try {
    const response = await chrome.runtime.sendMessage({ action: "callApi", numbers: numbers });
    if (response.success) {
      apiResults = response.data;
      // Ensure results are in same order as requested? Not necessary.
      renderResultsTable();
      resultsSection.style.display = "block";
      apiStatus.innerText = "API call successful.";
    } else {
      apiStatus.innerText = "API error: " + response.error;
    }
  } catch (err) {
    apiStatus.innerText = "API error: " + err.message;
  }
}

// Render results table with sorting/filtering
function renderResultsTable() {
  let filtered = [...apiResults];
  if (currentFilter !== "all") {
    filtered = filtered.filter(r => r.reputation === currentFilter);
  }
  // Sort
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
}

// Get top N numbers from current filtered/sorted table view
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
  const topNumbers = filtered.slice(0, n).map(r => r.phone_number);
  return topNumbers;
}

// Send selection to page
async function selectNumbersOnPage(numbers) {
  apiStatus.innerText = "Selecting numbers on page...";
  try {
    const response = await chrome.runtime.sendMessage({ action: "selectNumbersOnPage", numbers: numbers });
    if (response && response.success) {
      apiStatus.innerText = `Selected ${response.selected} numbers on page.`;
    } else {
      apiStatus.innerText = "Selection error: " + (response?.error || "unknown");
    }
  } catch (err) {
    apiStatus.innerText = "Selection error: " + err.message;
  }
}

// API URLs management
async function loadApiUrls() {
  const response = await chrome.runtime.sendMessage({ action: "getApiUrls" });
  renderApiUrls(response.urls);
}

function renderApiUrls(urls) {
  apiUrlsListDiv.innerHTML = "";
  urls.forEach((url, idx) => {
    const div = document.createElement("div");
    div.className = "api-url-item";
    div.innerHTML = `
      <input type="text" value="${url}" data-idx="${idx}" class="api-url-input">
      <button class="remove-url" data-idx="${idx}">❌</button>
    `;
    apiUrlsListDiv.appendChild(div);
  });
  // attach remove handlers
  document.querySelectorAll('.remove-url').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      const idx = parseInt(btn.dataset.idx);
      const newUrls = [...urls];
      newUrls.splice(idx, 1);
      await chrome.runtime.sendMessage({ action: "saveApiUrls", urls: newUrls });
      renderApiUrls(newUrls);
    });
  });
  // attach change handlers for inline editing
  document.querySelectorAll('.api-url-input').forEach(input => {
    input.addEventListener('change', async (e) => {
      const idx = parseInt(input.dataset.idx);
      const newUrls = [...urls];
      newUrls[idx] = input.value;
      await chrome.runtime.sendMessage({ action: "saveApiUrls", urls: newUrls });
    });
  });
}

// Event listeners
sendSelectedBtn.addEventListener("click", () => {
  if (selectedNumbersToSend.length === 0) {
    apiStatus.innerText = "No numbers selected.";
    return;
  }
  callApi(selectedNumbersToSend);
});

sendTopPageBtn.addEventListener("click", () => {
  let n = parseInt(topNPageInput.value);
  if (isNaN(n) || n <= 0) n = allPageNumbers.length;
  const topNumbers = allPageNumbers.slice(0, n);
  if (topNumbers.length === 0) {
    apiStatus.innerText = "No numbers on page.";
    return;
  }
  callApi(topNumbers);
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
    apiStatus.innerText = "No API results to select from.";
    return;
  }
  let n = parseInt(topNResultsInput.value);
  if (isNaN(n) || n <= 0) n = apiResults.length;
  const numbersToSelect = getTopResultsNumbers(n);
  if (numbersToSelect.length === 0) return;
  selectNumbersOnPage(numbersToSelect);
});

copyResultsBtn.addEventListener("click", async () => {
  const numbers = getTopResultsNumbers(999999); // all filtered/sorted
  if (numbers.length === 0) return;
  const text = numbers.join("\n");
  try {
    await navigator.clipboard.writeText(text);
    apiStatus.innerText = `Copied ${numbers.length} DIDs to clipboard.`;
  } catch (err) {
    apiStatus.innerText = "Copy failed: " + err.message;
  }
});

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
  }
});

// Initialization
loadPageNumbers();
loadApiUrls();