(() => {
  // ---- State ----
  const state = {
    currentStep: 1, // Track current step
    customers: [],
    filtered: [],
    selectedIds: new Set(),
    selectedExports: new Set(["storeproducts", "storedproducts", "packedproducts", "packedorders"]), // Default all selected
    status: "idle", // idle | running | done | failed
    startDate: "",
    endDate: "",
    editTargetId: null,
  };

  // ---- Elements ----
  const el = (id) => document.getElementById(id);

  const tabRun = el("tab-run");
  const tabCustomers = el("tab-customers");
  const panelRun = el("panel-run");
  const panelCustomers = el("panel-customers");

  const searchInput = el("searchInput");
  const customersList = el("customersList");
  const btnSelectAll = el("btn-select-all");
  const btnClearAll = el("btn-clear-all");

  const startDate = el("startDate");
  const endDate = el("endDate");
  const runMessage = el("runMessage");
  const btnStart = el("btn-start");
  const monthHalfControls = el("monthHalfControls");
  const rangeSummary = el("rangeSummary");
  const headerSelected = el("headerSelected");

  const statusChip = el("statusChip");
  const statusText = el("statusText");
  const summarySelected = el("summarySelected");
  const summaryDays = el("summaryDays");
  const summaryStatus = el("summaryStatus");
  const summaryRange = el("summaryRange");

  const formAdd = el("form-add");
  const addId = el("addId");
  const addName = el("addName");
  const customersTable = el("customersTable");
  const customersEmpty = el("customersEmpty");
  const customerSearch = el("customerSearch");

  // Modal
  const modal = el("modal");
  const modalTitle = el("modalTitle");
  const modalForm = el("modalForm");
  const modalId = el("modalId");
  const modalName = el("modalName");
  const modalIdErr = el("modalIdErr");
  const modalNameErr = el("modalNameErr");
  const modalCancel = el("modalCancel");

  // Toasts
  const toasts = el("toasts");

  // Recent downloads
  const recentDownloads = el("recentDownloads");
  const recentEmpty = el("recentEmpty");

  // Wizard buttons/cards
  const step1Card = document.getElementById("step1Card");
  const step2Card = document.getElementById("step2Card");
  const step3Card = document.getElementById("step3Card");
  const step4Card = document.getElementById("step4Card");
  const btnNext1 = document.getElementById("btnNext1");
  const btnBack2 = document.getElementById("btnBack2");
  const btnNext2 = document.getElementById("btnNext2");
  const btnBack3 = document.getElementById("btnBack3");
  const btnNext3 = document.getElementById("btnNext3");
  const btnBack4 = document.getElementById("btnBack4");
  const btnReset = document.getElementById("btnReset");
  
  // Export type buttons
  const btnSelectAllExports = document.getElementById("btn-select-all-exports");
  const btnClearAllExports = document.getElementById("btn-clear-all-exports");

  // ---- Utils ----
  function dayCount(a, b) {
    if (!a || !b) return 0;
    const start = new Date(a);
    const end = new Date(b);
    if (Number.isNaN(start) || Number.isNaN(end)) return 0;
    const diff = Math.abs(end - start);
    return Math.ceil(diff / (1000 * 60 * 60 * 24)) + 1;
  }

  function endOfMonth(date) {
    const d = new Date(date);
    return new Date(d.getFullYear(), d.getMonth() + 1, 0);
  }

  function formatISO(date) {
    // Always use local timezone - works globally
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }
  
  function parseLocalDate(dateString) {
    // Parse date string in user's local timezone
    const [year, month, day] = dateString.split('-').map(Number);
    return new Date(year, month - 1, day);
  }

  function debounce(fn, ms) {
    let t; return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
  }

  function showToast(type, message) {
    const id = `t-${Date.now()}`;
    const colors = type === "success" ? ["bg-green-600", "text-white"] : 
                  type === "error" ? ["bg-rose-600", "text-white"] : 
                  ["bg-slate-800", "text-white"];
    
    const div = document.createElement("div");
    div.id = id;
    div.className = `rounded-lg shadow px-4 py-2 pr-10 relative ${colors.join(" ")}`;
    
    // Add message and close button
    div.innerHTML = `
      <span>${message}</span>
      <button onclick="document.getElementById('${id}').remove()" 
              class="absolute top-1 right-2 text-white hover:text-gray-200 text-lg font-bold leading-none">
        ×
      </button>
    `;
    
    toasts.appendChild(div);
    
    // Auto-remove after longer duration
    const duration = type === "error" ? 8000 : 6000; // 8s for errors, 6s for success
    setTimeout(() => {
      if (document.getElementById(id)) {
        div.remove();
      }
    }, duration);
  }


  function updateRangeSummary() {
    const rangeSummaryCard = document.getElementById("rangeSummaryCard");
    if (state.startDate && state.endDate) {
      const start = new Date(state.startDate);
      const end = new Date(state.endDate);
      const options = { month: 'short', day: 'numeric', year: 'numeric' };
      const formattedRange = `${start.toLocaleDateString('en-US', options)} - ${end.toLocaleDateString('en-US', options)}`;
      
      rangeSummary.textContent = formattedRange;
      if (rangeSummaryCard) rangeSummaryCard.style.display = "block";
    } else {
      rangeSummary.textContent = "";
      if (rangeSummaryCard) rangeSummaryCard.style.display = "none";
    }
  }

  function updateSteps() {
    const step1 = document.getElementById("step1");
    const step2 = document.getElementById("step2");
    const step3 = document.getElementById("step3");
    const step4 = document.getElementById("step4");
    const bar12 = document.getElementById("bar12");
    const bar23 = document.getElementById("bar23");
    const bar34 = document.getElementById("bar34");

    const isStep1Active = state.currentStep >= 1;
    const isStep2Active = state.currentStep >= 2;
    const isStep3Active = state.currentStep >= 3;
    const isStep4Active = state.currentStep >= 4;

    // Step 1
    step1.querySelector("div").className = `w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
      isStep1Active ? "bg-blue-600 text-white" : "bg-slate-200"
    }`;
    step1.className = `flex items-center ${isStep1Active ? "text-blue-600" : "text-slate-400"}`;

    // Step 2
    step2.querySelector("div").className = `w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
      isStep2Active ? "bg-blue-600 text-white" : "bg-slate-200"
    }`;
    step2.className = `flex items-center ${isStep2Active ? "text-blue-600" : "text-slate-400"}`;
    bar12.className = `w-12 h-0.5 ${isStep2Active ? "bg-blue-600" : "bg-slate-300"}`;

    // Step 3
    step3.querySelector("div").className = `w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
      isStep3Active ? "bg-blue-600 text-white" : "bg-slate-200"
    }`;
    step3.className = `flex items-center ${isStep3Active ? "text-blue-600" : "text-slate-400"}`;
    bar23.className = `w-12 h-0.5 ${isStep3Active ? "bg-blue-600" : "bg-slate-200"}`;

    // Step 4
    step4.querySelector("div").className = `w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
      isStep4Active ? "bg-blue-600 text-white" : "bg-slate-200"
    }`;
    step4.className = `flex items-center ${isStep4Active ? "text-blue-600" : "text-slate-400"}`;
    bar34.className = `w-12 h-0.5 ${isStep4Active ? "bg-blue-600" : "bg-slate-200"}`;
  }

  function formatDateRange(start, end) {
    if (!start || !end) return "Not set";
    // Use timezone-safe parsing
    const startDate = parseLocalDate(start);
    const endDate = parseLocalDate(end);
    const options = { month: 'short', day: 'numeric' };
    
    // If same year, don't repeat it
    if (startDate.getFullYear() === endDate.getFullYear()) {
      return `${startDate.toLocaleDateString('en-US', options)} - ${endDate.toLocaleDateString('en-US', options)}, ${startDate.getFullYear()}`;
    }
    return `${startDate.toLocaleDateString('en-US', {...options, year: 'numeric'})} - ${endDate.toLocaleDateString('en-US', {...options, year: 'numeric'})}`;
  }

  function getStatusText() {
    if (state.status === "running") return "Downloading";
    if (state.status === "done") return "Completed";
    if (state.status === "failed") return "Failed";
    
    if (state.currentStep === 1) return "Select Customers";
    if (state.currentStep === 2) return "Set Date Range";
    if (state.currentStep === 3) return "Choose Export Types";
    if (state.currentStep === 4) return "Ready";
    return "Pending";
  }

  function getStatusClass() {
    if (state.status === "running") return "bg-blue-100 text-blue-800";
    if (state.status === "done") return "bg-green-100 text-green-800";
    if (state.status === "failed") return "bg-red-100 text-red-800";
    
    // Green when ready to download, gray otherwise
    if (state.currentStep === 4 && state.selectedIds.size > 0 && state.startDate && state.endDate && state.selectedExports.size > 0) {
      return "bg-green-100 text-green-800";
    }
    return "bg-gray-100 text-gray-800";
  }

  function updateSummaries() {
    // Update header
    headerSelected.textContent = state.selectedIds.size;
    
    // Update sidebar summary with better formatting
    summarySelected.textContent = `${state.selectedIds.size} selected`;
    const summaryDaysDisplay = document.getElementById("summaryDaysDisplay");
    if (summaryDaysDisplay) {
      summaryDaysDisplay.textContent = formatDateRange(state.startDate, state.endDate);
    }
    const summaryExportTypes = document.getElementById("summaryExportTypes");
    if (summaryExportTypes) {
      summaryExportTypes.textContent = `${state.selectedExports.size} selected`;
    }
    
    // Update dynamic status badge like ui_demo
    const summaryStatusBadge = document.getElementById("summaryStatusBadge");
    if (summaryStatusBadge) {
      summaryStatusBadge.textContent = getStatusText();
      summaryStatusBadge.className = `px-2 py-1 text-xs rounded-full ${getStatusClass()}`;
    }
    
    // Update step 3 summary cards with better date range display
    const summaryCustomersCount = document.getElementById("summaryCustomersCount");
    const summaryDaysCount = document.getElementById("summaryDaysCount");
    const summaryFilesCount = document.getElementById("summaryFilesCount");
    
    if (summaryCustomersCount) summaryCustomersCount.textContent = state.selectedIds.size;
    if (summaryDaysCount) {
      // Show formatted date range instead of day count
      const dateRange = formatDateRange(state.startDate, state.endDate);
      summaryDaysCount.textContent = dateRange !== "Not set" ? dateRange : "Not set";
    }
    if (summaryFilesCount) summaryFilesCount.textContent = state.selectedIds.size * state.selectedExports.size; // Dynamic file count
    
    // Update download button state
    btnStart.disabled = !(state.selectedIds.size > 0 && state.startDate && state.endDate && state.selectedExports.size > 0);
    
    // Update range summary
    updateRangeSummary();
    updateSteps();
    
    // Update navigation buttons
    btnNext1.disabled = state.selectedIds.size === 0;
    btnNext2.disabled = !(state.startDate && state.endDate);
    btnNext3.disabled = state.selectedExports.size === 0;
  }

  function renderCustomerCard(cust) {
    const checked = state.selectedIds.has(cust.id) ? "checked" : "";
    const selectedClass = state.selectedIds.has(cust.id) ? "bg-blue-50 border-blue-200" : "";
    return `
      <label class="flex items-center p-3 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer transition-all duration-200 ${selectedClass}">
        <input type="checkbox" data-id="${cust.id}" class="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500" ${checked} />
        <div class="ml-3 flex-1">
          <div class="flex items-center justify-between">
            <span class="text-sm font-medium text-gray-900">${cust.name || "Unnamed"}</span>
            <span class="text-xs text-gray-500">ID ${cust.id}</span>
          </div>
        </div>
      </label>
    `;
  }

  function applyFilter() {
    const q = (searchInput.value || "").toLowerCase();
    state.filtered = state.customers.filter((c) =>
      String(c.id).includes(q) || (c.name || "").toLowerCase().includes(q)
    );
    customersList.innerHTML = state.filtered.map(renderCustomerCard).join("");
  }

  function renderCustomersTable() {
    const q = (customerSearch.value || "").toLowerCase();
    const rows = state.customers
      .filter((c) => String(c.id).includes(q) || (c.name || "").toLowerCase().includes(q))
      .sort((a, b) => a.id - b.id)
      .map((c) => `
        <tr>
          <td class="px-4 py-2">${c.id}</td>
          <td class="px-4 py-2">${c.name || ""}</td>
          <td class="px-4 py-2 text-right space-x-2">
            <button data-edit="${c.id}" class="px-2 py-1 text-xs rounded bg-slate-100 hover:bg-slate-200">Edit</button>
            <button data-del="${c.id}" class="px-2 py-1 text-xs rounded bg-rose-50 text-rose-700 hover:bg-rose-100">Delete</button>
          </td>
        </tr>`)
      .join("");
    customersTable.innerHTML = rows;
    customersEmpty.classList.toggle("hidden", state.customers.length !== 0);
  }

  function setStatus(s) {
    state.status = s;
    updateSummaries();
    
    // Add visual feedback for status changes
    if (s === "running") {
      btnStart.disabled = true;
    } else if (s === "done") {
      // Re-enable after a delay
      setTimeout(() => {
        btnStart.disabled = !(state.selectedIds.size > 0 && state.startDate && state.endDate);
      }, 2000);
    } else if (s === "failed") {
      btnStart.disabled = !(state.selectedIds.size > 0 && state.startDate && state.endDate);
    }
  }

  // ---- Fetch helpers ----
  async function getJSON(url) {
    const res = await fetch(url);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }

  async function sendJSON(url, method, body) {
    const res = await fetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data?.error || "Request failed");
    return data;
  }

  // ---- Customers CRUD ----
  async function loadCustomers() {
    try {
      const data = await getJSON("/api/customers");
      state.customers = Array.isArray(data.items) ? data.items : [];
    } catch {
      state.customers = [];
    }
    state.selectedIds.clear();
    applyFilter();
    renderCustomersTable();
    updateSummaries();
  }

  async function addCustomerHandler(e) {
    e.preventDefault();
    const idVal = Number(addId.value);
    const nameVal = (addName.value || "").trim();
    if (!idVal || !Number.isFinite(idVal)) {
      showToast("error", "ID must be a numeric value");
      return;
    }
    if (!nameVal) {
      showToast("error", "Name is required");
      return;
    }
    try {
      await sendJSON("/api/customers", "POST", { id: idVal, name: nameVal });
      addId.value = "";
      addName.value = "";
      showToast("success", "Customer added");
      await loadCustomers();
    } catch (e) {
      showToast("error", e.message || "Failed to add customer");
    }
  }

  function openEditModal(id) {
    const c = state.customers.find((x) => x.id === id);
    if (!c) return;
    state.editTargetId = id;
    modalTitle.textContent = "Edit Customer";
    modalId.value = c.id;
    modalName.value = c.name || "";
    modal.classList.add("open");
    modalIdErr.classList.add("hidden");
    modalNameErr.classList.add("hidden");
    setTimeout(() => modalId.focus(), 0);
  }

  function closeModal() {
    modal.classList.remove("open");
    state.editTargetId = null;
  }

  async function submitEditModal(e) {
    e.preventDefault();
    const idVal = Number(modalId.value);
    const nameVal = (modalName.value || "").trim();
    let valid = true;
    if (!idVal || !Number.isFinite(idVal)) {
      modalIdErr.textContent = "ID must be numeric";
      modalIdErr.classList.remove("hidden");
      valid = false;
    } else {
      modalIdErr.classList.add("hidden");
    }
    if (!nameVal) {
      modalNameErr.textContent = "Name cannot be empty";
      modalNameErr.classList.remove("hidden");
      valid = false;
    } else {
      modalNameErr.classList.add("hidden");
    }
    if (!valid) return;
    try {
      await sendJSON(`/api/customers/${state.editTargetId}`, "PUT", { id: idVal, name: nameVal });
      showToast("success", "Customer updated");
      closeModal();
      await loadCustomers();
    } catch (e) {
      showToast("error", e.message || "Update failed");
    }
  }

  async function confirmDelete(id) {
    const c = state.customers.find((x) => x.id === id);
    if (!c) return;
    state.editTargetId = id;
    modalTitle.textContent = "Delete Customer";
    modalId.value = c.id;
    modalName.value = c.name || "";
    modalId.disabled = true;
    modalName.disabled = true;
    const saveBtn = document.getElementById("modalSave");
    saveBtn.textContent = "Delete";
    saveBtn.classList.remove("bg-blue-600");
    saveBtn.classList.add("bg-rose-600");
    modal.classList.add("open");

    modalForm.onsubmit = async (e) => {
      e.preventDefault();
      try {
        const res = await fetch(`/api/customers/${id}`, { method: "DELETE" });
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data?.error || "Delete failed");
        }
        showToast("success", "Customer deleted");
        closeModal();
        // reset modal state
        saveBtn.textContent = "Save";
        saveBtn.classList.remove("bg-rose-600");
        saveBtn.classList.add("bg-blue-600");
        modalId.disabled = false; modalName.disabled = false;
        modalForm.onsubmit = submitEditModal;
        await loadCustomers();
      } catch (e) {
        showToast("error", e.message || "Delete failed");
      }
    };
  }

  // ---- UI Blocking Functions ----
  function blockUI() {
    // Disable navigation tabs
    tabRun.style.pointerEvents = 'none';
    tabCustomers.style.pointerEvents = 'none';
    
    // Add refresh warning
    window.addEventListener('beforeunload', preventRefresh);
  }
  
  function unblockUI() {
    // Re-enable navigation tabs
    tabRun.style.pointerEvents = 'auto';
    tabCustomers.style.pointerEvents = 'auto';
    
    // Remove refresh warning
    window.removeEventListener('beforeunload', preventRefresh);
  }
  
  function preventRefresh(e) {
    e.preventDefault();
    e.returnValue = 'Download in progress. Are you sure you want to leave?';
    return e.returnValue;
  }
  
  // ---- Download Status Polling ----
  function pollDownloadStatus(taskId) {
    const pollInterval = setInterval(async () => {
      try {
        const status = await getJSON(`/api/run/status/${taskId}`);
        
        if (status.status === "completed") {
          setStatus("done");
          runMessage.textContent = `✅ ${status.message}`;
          showToast("success", status.message);
          setTimeout(loadRecentDownloads, 500);
          unblockUI();
          resetDownloadButton();
          clearInterval(pollInterval);
        } else if (status.status === "failed") {
          setStatus("failed");
          runMessage.textContent = `❌ ${status.message}`;
          showToast("error", status.message);
          unblockUI();
          resetDownloadButton();
          clearInterval(pollInterval);
        }
        // Keep polling if status is "running"
      } catch (error) {
        console.error("Status poll failed:", error);
      }
    }, 3000); // Poll every 3 seconds
  }
  
  function resetDownloadButton() {
    const downloadIcon = document.getElementById("downloadIcon");
    const loadingIcon = document.getElementById("loadingIcon");
    const downloadText = document.getElementById("downloadText");
    
    if (downloadIcon) downloadIcon.style.display = "inline";
    if (loadingIcon) loadingIcon.style.display = "none";
    if (downloadText) downloadText.textContent = "Start Download";
  }

  // ---- Run ----
  async function startRun() {
    try {
      setStatus("running");
      blockUI();
      
      // Update button to loading state
      const downloadIcon = document.getElementById("downloadIcon");
      const loadingIcon = document.getElementById("loadingIcon");
      const downloadText = document.getElementById("downloadText");
      
      if (downloadIcon) downloadIcon.style.display = "none";
      if (loadingIcon) loadingIcon.style.display = "inline";
      if (downloadText) downloadText.textContent = "Downloading...";
      
      runMessage.classList.remove("hidden");
      runMessage.textContent = "Starting download process...";
      
      const api_user_ids = Array.from(state.selectedIds);
      const export_types = Array.from(state.selectedExports);
      const payload = { api_user_ids, start_date: state.startDate, end_date: state.endDate, export_types };
      const data = await sendJSON("/api/run", "POST", payload);
      
      if (data.task_id) {
        runMessage.textContent = "Download in progress...";
        // Start polling for status updates
        pollDownloadStatus(data.task_id);
      } else {
        throw new Error("Failed to start download task");
      }
      
    } catch (e) {
      setStatus("failed");
      runMessage.textContent = `❌ ${e.message || "Failed to start download"}`;
      showToast("error", e.message || "Failed to start download");
      unblockUI();
      resetDownloadButton();
    }
  }

  // ---- Presets ----
  let currentMonthPreset = null; // Track the active month preset
  
  function highlightActivePreset(activePreset, isHalfMonth = false) {
    // Reset all preset buttons
    document.querySelectorAll(".preset-btn").forEach(btn => {
      btn.classList.remove("bg-blue-100", "text-blue-700", "border-blue-300");
      btn.classList.add("bg-gray-100", "text-gray-700");
    });
    
    // For half-month selections, keep both month and half active
    if (isHalfMonth && currentMonthPreset) {
      const monthBtn = document.querySelector(`[data-preset="${currentMonthPreset}"]`);
      if (monthBtn) {
        monthBtn.classList.remove("bg-gray-100", "text-gray-700");
        monthBtn.classList.add("bg-blue-100", "text-blue-700", "border-blue-300");
      }
    }
    
    // Highlight active preset
    if (activePreset) {
      const activeBtn = document.querySelector(`[data-preset="${activePreset}"]`);
      if (activeBtn) {
        activeBtn.classList.remove("bg-gray-100", "text-gray-700");
        activeBtn.classList.add("bg-blue-100", "text-blue-700", "border-blue-300");
      }
    }
  }

  let lastSelectedMonth = null;
  let isThisMonth = false; // Track if we're working with current month
  
  function updateHalfMonthOptions() {
    const today = new Date();
    const currentDay = today.getDate();
    
    // Get half-month buttons
    const firstHalfBtn = document.querySelector('[data-preset="firstHalf"]');
    const secondHalfBtn = document.querySelector('[data-preset="secondHalf"]');
    const fullMonthBtn = document.querySelector('[data-preset="fullMonth"]');
    
    // Always hide "Full month" - it's redundant
    if (fullMonthBtn) fullMonthBtn.style.display = 'none';
    
    if (isThisMonth) {
      // Smart visibility based on current date
      if (currentDay <= 15) {
        // Before 16th: Hide all options (default is already 1-today)
        if (firstHalfBtn) firstHalfBtn.style.display = 'none';
        if (secondHalfBtn) secondHalfBtn.style.display = 'none';
      } else {
        // After 15th: Show first half only, hide second half
        if (firstHalfBtn) firstHalfBtn.style.display = 'inline-block';
        if (secondHalfBtn) secondHalfBtn.style.display = 'none';
      }
    } else {
      // For "Last Month", show both halves
      if (firstHalfBtn) firstHalfBtn.style.display = 'inline-block';
      if (secondHalfBtn) {
        secondHalfBtn.style.display = 'inline-block';
        secondHalfBtn.textContent = 'Second half (16–End)';
      }
    }
  }
  
  function setPreset(preset) {
    const today = new Date();
    const iso = (d) => formatISO(d);

    const showMonthHalves = () => {
      monthHalfControls.classList.remove("hidden");
      // Use setTimeout to ensure DOM is updated before hiding buttons
      setTimeout(() => updateHalfMonthOptions(), 0);
    };
    const hideMonthHalves = () => monthHalfControls.classList.add("hidden");

    if (preset === "today") {
      hideMonthHalves();
      currentMonthPreset = null;
      isThisMonth = false;
      state.startDate = iso(today);
      state.endDate = iso(today);
    } else if (preset === "yesterday") {
      hideMonthHalves();
      currentMonthPreset = null;
      isThisMonth = false;
      const y = new Date(today); y.setDate(today.getDate() - 1);
      state.startDate = iso(y);
      state.endDate = iso(y);
    } else if (preset === "thisWeek") {
      hideMonthHalves();
      currentMonthPreset = null;
      isThisMonth = false;
      const s = new Date(today); s.setDate(today.getDate() - today.getDay());
      state.startDate = iso(s);
      state.endDate = iso(today);
    } else if (preset === "lastWeek") {
      hideMonthHalves();
      currentMonthPreset = null;
      isThisMonth = false;
      const e = new Date(today); e.setDate(today.getDate() - today.getDay() - 1);
      const s = new Date(e); s.setDate(e.getDate() - 6);
      state.startDate = iso(s);
      state.endDate = iso(e);
    } else if (preset === "thisMonth") {
      showMonthHalves();
      currentMonthPreset = "thisMonth";
      isThisMonth = true;
      lastSelectedMonth = new Date(today.getFullYear(), today.getMonth(), 1);
      const s = new Date(today.getFullYear(), today.getMonth(), 1);
      state.startDate = iso(s);
      state.endDate = iso(today);
    } else if (preset === "lastMonth") {
      showMonthHalves();
      currentMonthPreset = "lastMonth";
      isThisMonth = false;
      lastSelectedMonth = new Date(today.getFullYear(), today.getMonth() - 1, 1);
      const s = new Date(today.getFullYear(), today.getMonth() - 1, 1);
      const e = new Date(today.getFullYear(), today.getMonth(), 0);
      state.startDate = iso(s);
      state.endDate = iso(e);
    } else if (preset === "firstHalf") {
      const baseMonth = lastSelectedMonth || new Date(today.getFullYear(), today.getMonth(), 1);
      const s = new Date(baseMonth.getFullYear(), baseMonth.getMonth(), 1);
      const e = new Date(baseMonth.getFullYear(), baseMonth.getMonth(), 15);
      state.startDate = iso(s);
      state.endDate = iso(e);
    } else if (preset === "secondHalf") {
      const baseMonth = lastSelectedMonth || new Date(today.getFullYear(), today.getMonth(), 1);
      const s = new Date(baseMonth.getFullYear(), baseMonth.getMonth(), 16);
      
      // Smart end date calculation
      let e;
      if (isThisMonth) {
        // For "This Month" -> "Second Half", end on today
        e = today;
      } else {
        // For "Last Month" -> "Second Half", end on last day of that month
        e = endOfMonth(baseMonth);
      }
      
      state.startDate = iso(s);
      state.endDate = iso(e);
    } else if (preset === "fullMonth") {
      const baseMonth = lastSelectedMonth || new Date(today.getFullYear(), today.getMonth(), 1);
      const s = new Date(baseMonth.getFullYear(), baseMonth.getMonth(), 1);
      
      // Smart end date calculation
      let e;
      if (isThisMonth) {
        // For "This Month" -> "Full Month", end on today
        e = today;
      } else {
        // For "Last Month" -> "Full Month", end on last day of that month
        e = endOfMonth(baseMonth);
      }
      
      state.startDate = iso(s);
      state.endDate = iso(e);
    }
    
    // Update form inputs
    startDate.value = state.startDate;
    endDate.value = state.endDate;
    
    // Highlight active preset and update summaries
    const isHalfMonth = ["firstHalf", "secondHalf", "fullMonth"].includes(preset);
    highlightActivePreset(preset, isHalfMonth);
    updateSummaries();
  }

  // ---- Tab logic with gating ----
  function gotoTab(name) {
    const canProceedToRun = state.customers.length > 0;
    if (name === "customers") {
      panelRun.classList.add("hidden");
      panelCustomers.classList.remove("hidden");
      tabRun.classList.remove("border-blue-600", "text-blue-600");
      tabCustomers.classList.add("border-blue-600", "text-blue-600");
      return;
    }
    if (!canProceedToRun) {
      showToast("error", "Please add at least one customer first.");
      return;
    }
    panelCustomers.classList.add("hidden");
    panelRun.classList.remove("hidden");
    tabCustomers.classList.remove("border-blue-600", "text-blue-600");
    tabRun.classList.add("border-blue-600", "text-blue-600");
  }

  // ---- Wizard nav ----
  function showStep(step) {
    state.currentStep = step;
    step1Card.classList.toggle("hidden", step !== 1);
    step2Card.classList.toggle("hidden", step !== 2);
    step3Card.classList.toggle("hidden", step !== 3);
    step4Card.classList.toggle("hidden", step !== 4);
    updateSteps();
    updateSummaries();
  }

  // ADD: Simple navigation functions like ui_demo
  function nextStep() {
    if (state.currentStep < 4) {
      showStep(state.currentStep + 1);
    }
  }

  function prevStep() {
    if (state.currentStep > 1) {
      showStep(state.currentStep - 1);
    }
  }

  function resetWizard() {
    state.selectedIds.clear();
    state.selectedExports.clear();
    state.selectedExports.add("storeproducts");
    state.selectedExports.add("storedproducts");
    state.selectedExports.add("packedproducts");
    state.selectedExports.add("packedorders");
    state.startDate = "";
    state.endDate = "";
    startDate.value = "";
    endDate.value = "";
    // Reset export checkboxes
    document.querySelectorAll('[data-export-type]').forEach(cb => cb.checked = true);
    showStep(1);
    runMessage.classList.add("hidden");
    runMessage.textContent = "";
    setStatus("idle");
    applyFilter();
    updateSummaries();
  }

  // ---- Events ----
  tabRun.addEventListener("click", () => gotoTab("run"));
  tabCustomers.addEventListener("click", () => gotoTab("customers"));

  searchInput.addEventListener("input", debounce(applyFilter, 200));
  customerSearch.addEventListener("input", debounce(renderCustomersTable, 200));

  customersList.addEventListener("change", (e) => {
    const id = Number(e.target.getAttribute("data-id"));
    if (!id) return;
    if (e.target.checked) state.selectedIds.add(id);
    else state.selectedIds.delete(id);
    updateSummaries();
  });

  btnSelectAll.addEventListener("click", () => {
    state.filtered.forEach((c) => state.selectedIds.add(c.id));
    applyFilter();
    updateSummaries();
  });

  btnClearAll.addEventListener("click", () => {
    state.selectedIds.clear();
    applyFilter();
    updateSummaries();
  });

  document.querySelectorAll(".preset-btn").forEach((b) => {
    b.addEventListener("click", () => setPreset(b.dataset.preset));
  });

  startDate.addEventListener("change", () => {
    state.startDate = startDate.value;
    updateSummaries();
  });
  endDate.addEventListener("change", () => {
    state.endDate = endDate.value;
    updateSummaries();
  });

  btnStart.addEventListener("click", startRun);

  btnNext1.addEventListener("click", () => { if (state.selectedIds.size > 0) nextStep(); });
  btnBack2.addEventListener("click", prevStep);
  btnNext2.addEventListener("click", () => { if (state.startDate && state.endDate) nextStep(); });
  btnBack3.addEventListener("click", prevStep);
  btnNext3.addEventListener("click", () => { if (state.selectedExports.size > 0) nextStep(); });
  btnBack4.addEventListener("click", prevStep);
  btnReset.addEventListener("click", resetWizard);
  
  // Export type selection events
  document.addEventListener("change", (e) => {
    if (e.target.matches('[data-export-type]')) {
      const exportType = e.target.getAttribute("data-export-type");
      if (e.target.checked) {
        state.selectedExports.add(exportType);
      } else {
        state.selectedExports.delete(exportType);
      }
      updateSummaries();
    }
  });
  
  btnSelectAllExports.addEventListener("click", () => {
    document.querySelectorAll('[data-export-type]').forEach(cb => {
      cb.checked = true;
      state.selectedExports.add(cb.getAttribute("data-export-type"));
    });
    updateSummaries();
  });
  
  btnClearAllExports.addEventListener("click", () => {
    document.querySelectorAll('[data-export-type]').forEach(cb => {
      cb.checked = false;
      state.selectedExports.delete(cb.getAttribute("data-export-type"));
    });
    updateSummaries();
  });

  customersTable.addEventListener("click", (e) => {
    const editId = e.target.getAttribute("data-edit");
    const delId = e.target.getAttribute("data-del");
    if (editId) openEditModal(Number(editId));
    if (delId) confirmDelete(Number(delId));
  });

  formAdd.addEventListener("submit", addCustomerHandler);

  // Modal wiring
  modalCancel.addEventListener("click", () => {
    // reset destructive state if needed
    const saveBtn = document.getElementById("modalSave");
    saveBtn.textContent = "Save";
    saveBtn.classList.remove("bg-rose-600");
    saveBtn.classList.add("bg-blue-600");
    modalId.disabled = false; modalName.disabled = false;
    modalForm.onsubmit = submitEditModal;
    closeModal();
  });
  modalForm.addEventListener("submit", submitEditModal);
  modal.addEventListener("click", (e) => { if (e.target === modal) modalCancel.click(); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && modal.classList.contains("open")) modalCancel.click(); });

  // ---- Init ----
  async function loadRecentDownloads() {
    try {
      const data = await getJSON("/api/recent-downloads");
      const items = Array.isArray(data.items) ? data.items : [];
      recentDownloads.innerHTML = items.map((it) => {
        const files = it.file_count ?? 0;
        const name = it.name || "";
        let timeAgo = "";
        if (it.created_at) {
          const d = new Date(it.created_at);
          const now = new Date();
          
          // Check if same day
          const isToday = d.toDateString() === now.toDateString();
          if (isToday) {
            timeAgo = "Today";
          } else {
            const diffMs = now - d;
            const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
            
            if (diffDays <= 0) {
              timeAgo = "Today"; // Handle edge case where diffDays is 0 but different day
            } else if (diffDays === 1) {
              timeAgo = "Yesterday";
            } else if (diffDays < 7) {
              timeAgo = `${diffDays} days ago`;
            } else if (diffDays < 30) {
              const weeks = Math.floor(diffDays / 7);
              timeAgo = `${weeks} week${weeks > 1 ? 's' : ''} ago`;
            } else {
              const months = Math.floor(diffDays / 30);
              timeAgo = `${months} month${months > 1 ? 's' : ''} ago`;
            }
          }
        }
        
        const statusClass = files > 0 ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800";
        const statusText = files > 0 ? "success" : "failed";
        
        return `<div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
          <div>
            <div class="text-sm font-medium text-gray-900">${name}</div>
            <div class="text-xs text-gray-500">${timeAgo}</div>
          </div>
          <div class="flex items-center space-x-2">
            <span class="text-xs px-2 py-1 rounded-full ${statusClass}">${files} files</span>
          </div>
        </div>`;
      }).join("");
      recentEmpty.classList.toggle("hidden", items.length > 0);
    } catch {
      recentDownloads.innerHTML = "";
      recentEmpty.classList.remove("hidden");
    }
  }

  loadCustomers().then(() => gotoTab("run"));
  loadRecentDownloads();
  showStep(1);
})();
