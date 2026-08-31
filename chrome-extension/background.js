/**
 * Background Service Worker (Manifest V3)
 * Receives scraped WhatsApp payload from content script and syncs to Dashboard API.
 */

console.log("[WhatsApp Scraper] Background service worker initialized.");

// Default Settings
const DEFAULT_SETTINGS = {
    dashboardUrl: "http://127.0.0.1:8000",
    apiToken: "",
    isScrapingActive: false,
    targetGroupFilter: "",
    totalSyncedCount: 0,
    lastSyncTime: null,
    syncLogs: []
};

// Ensure settings exist in storage
chrome.runtime.onInstalled.addListener(() => {
    chrome.storage.local.get(Object.keys(DEFAULT_SETTINGS), (result) => {
        const updates = {};
        for (let key in DEFAULT_SETTINGS) {
            if (result[key] === undefined) {
                updates[key] = DEFAULT_SETTINGS[key];
            }
        }
        if (Object.keys(updates).length > 0) {
            chrome.storage.local.set(updates);
        }
    });
});

// Handle incoming messages from content script or popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "INGEST_MESSAGES") {
        syncMessagesToBackend(request.payload.messages);
        sendResponse({ status: "RECEIVED" });
    }
    return true;
});

async function syncMessagesToBackend(messages) {
    if (!messages || messages.length === 0) return;

    chrome.storage.local.get(["dashboardUrl", "apiToken", "totalSyncedCount", "syncLogs"], async (data) => {
        let baseUrl = (data.dashboardUrl || "http://127.0.0.1:8000").replace(/\/$/, "");
        const token = data.apiToken;

        if (!token) {
            logSyncEvent("ERROR", "Client API Token missing! Please configure in Extension Popup.");
            return;
        }

        const endpoint = `${baseUrl}/api/whatsapp/ingest`;
        try {
            const response = await fetch(endpoint, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-Client-Token": token
                },
                body: JSON.stringify({
                    api_token: token,
                    messages: messages
                })
            });

            const result = await response.json();
            if (response.ok && result.status === "success") {
                const added = result.ingested_count || messages.length;
                const newTotal = (data.totalSyncedCount || 0) + added;
                const nowStr = new Date().toLocaleTimeString();

                chrome.storage.local.set({
                    totalSyncedCount: newTotal,
                    lastSyncTime: nowStr
                });

                logSyncEvent("SUCCESS", `Synced ${added} messages to dashboard at ${nowStr}`);
            } else {
                logSyncEvent("ERROR", `Sync failed: ${result.detail || result.message || 'HTTP ' + response.status}`);
            }
        } catch (err) {
            logSyncEvent("ERROR", `Network Error: ${err.message}`);
        }
    });
}

function logSyncEvent(type, message) {
    chrome.storage.local.get(["syncLogs"], (data) => {
        const logs = data.syncLogs || [];
        logs.unshift({
            timestamp: new Date().toLocaleTimeString(),
            type: type,
            message: message
        });
        // Keep last 50 logs
        if (logs.length > 50) logs.pop();
        chrome.storage.local.set({ syncLogs: logs });
    });
}
