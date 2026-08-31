document.addEventListener("DOMContentLoaded", () => {
    const scrapeToggle = document.getElementById("scrapeToggle");
    const statusBadge = document.getElementById("statusBadge");
    const dashboardUrl = document.getElementById("dashboardUrl");
    const apiToken = document.getElementById("apiToken");
    const targetGroup = document.getElementById("targetGroup");
    const saveConfigBtn = document.getElementById("saveConfigBtn");
    const totalCount = document.getElementById("totalCount");
    const lastSync = document.getElementById("lastSync");
    const logsContainer = document.getElementById("logsContainer");
    const clearLogsBtn = document.getElementById("clearLogsBtn");

    // Load initial state from storage
    chrome.storage.local.get([
        "dashboardUrl", "apiToken", "isScrapingActive", 
        "targetGroupFilter", "totalSyncedCount", "lastSyncTime", "syncLogs"
    ], (data) => {
        if (data.dashboardUrl) dashboardUrl.value = data.dashboardUrl;
        if (data.apiToken) apiToken.value = data.apiToken;
        if (data.targetGroupFilter) targetGroup.value = data.targetGroupFilter;
        
        scrapeToggle.checked = !!data.isScrapingActive;
        updateBadge(!!data.isScrapingActive);

        totalCount.innerText = data.totalSyncedCount || 0;
        lastSync.innerText = data.lastSyncTime || "--:--";

        renderLogs(data.syncLogs || []);
    });

    // Save Settings
    saveConfigBtn.addEventListener("click", () => {
        const urlVal = dashboardUrl.value.trim();
        const tokenVal = apiToken.value.trim();
        const groupVal = targetGroup.value.trim();

        chrome.storage.local.set({
            dashboardUrl: urlVal,
            apiToken: tokenVal,
            targetGroupFilter: groupVal
        }, () => {
            saveConfigBtn.innerText = "Saved!";
            setTimeout(() => saveConfigBtn.innerText = "Save Settings", 1500);

            // Notify Content Script if active
            if (scrapeToggle.checked) {
                notifyContentScript(true, groupVal);
            }
        });
    });

    // Master Scraping Toggle
    scrapeToggle.addEventListener("change", (e) => {
        const enabled = e.target.checked;
        chrome.storage.local.set({ isScrapingActive: enabled });
        updateBadge(enabled);
        notifyContentScript(enabled, targetGroup.value.trim());
    });

    // Clear Logs
    clearLogsBtn.addEventListener("click", () => {
        chrome.storage.local.set({ syncLogs: [] }, () => {
            renderLogs([]);
        });
    });

    function updateBadge(enabled) {
        if (enabled) {
            statusBadge.innerText = "ACTIVE";
            statusBadge.className = "status-badge badge-on";
        } else {
            statusBadge.innerText = "OFF";
            statusBadge.className = "status-badge badge-off";
        }
    }

    function notifyContentScript(enabled, group) {
        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
            if (tabs && tabs[0]) {
                chrome.tabs.sendMessage(tabs[0].id, {
                    action: "TOGGLE_SCRAPING",
                    enabled: enabled,
                    targetGroup: group
                }, (response) => {
                    if (chrome.runtime.lastError) {
                        console.log("Tab message response:", chrome.runtime.lastError.message);
                    }
                });
            }
        });
    }

    function renderLogs(logs) {
        if (!logs || logs.length === 0) {
            logsContainer.innerHTML = '<div class="log-empty">No sync logs recorded yet.</div>';
            return;
        }

        logsContainer.innerHTML = logs.map(item => `
            <div class="log-item ${item.type}">
                <span>[${item.timestamp}]</span> ${item.message}
            </div>
        `).join('');
    }
});
