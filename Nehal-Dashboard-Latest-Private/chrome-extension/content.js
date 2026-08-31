/**
 * WhatsApp Web DOM Observer & Data Extractor (Manifest V3 Content Script)
 * Monitors active chat in https://web.whatsapp.com and extracts incoming/existing messages.
 */

console.log("[WhatsApp Scraper] Content script loaded on WhatsApp Web.");

let isScrapingActive = false;
let targetGroupFilter = "";
let processedMessageIds = new Set();
let observer = null;

// Initialize config from Chrome Storage
chrome.storage.local.get(["isScrapingActive", "targetGroupFilter"], (result) => {
    isScrapingActive = result.isScrapingActive !== undefined ? result.isScrapingActive : false;
    targetGroupFilter = result.targetGroupFilter || "";
    if (isScrapingActive) {
        startDOMObserver();
    }
});

// Listen for messages from Popup or Background
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "TOGGLE_SCRAPING") {
        isScrapingActive = request.enabled;
        targetGroupFilter = request.targetGroup || "";
        if (isScrapingActive) {
            startDOMObserver();
            scrapeCurrentChat();
            sendResponse({ status: "STARTED" });
        } else {
            stopDOMObserver();
            sendResponse({ status: "STOPPED" });
        }
    } else if (request.action === "MANUAL_EXPORT") {
        const scrapedCount = scrapeCurrentChat();
        sendResponse({ count: scrapedCount });
    }
    return true;
});

function startDOMObserver() {
    stopDOMObserver();
    console.log("[WhatsApp Scraper] Starting DOM Observer...");

    observer = new MutationObserver((mutations) => {
        if (!isScrapingActive) return;
        scrapeCurrentChat();
    });

    const targetNode = document.getElementById("app") || document.body;
    observer.observe(targetNode, {
        childList: true,
        subtree: true
    });
}

function stopDOMObserver() {
    if (observer) {
        observer.disconnect();
        observer = null;
        console.log("[WhatsApp Scraper] Observer disconnected.");
    }
}

function scrapeCurrentChat() {
    if (!isScrapingActive) return 0;

    // Get Active Chat / Group Name
    const headerEl = document.querySelector("#main header") || document.querySelector("header");
    if (!headerEl) return 0;

    let groupName = "General Chat";
    const titleEl = headerEl.querySelector('[title], [dir="auto"]');
    if (titleEl && titleEl.innerText) {
        groupName = titleEl.innerText.trim();
    }

    // Check target group filter
    if (targetGroupFilter && targetGroupFilter.trim()) {
        const filterTerm = targetGroupFilter.trim().toLowerCase();
        if (!groupName.toLowerCase().includes(filterTerm)) {
            return 0; // Skip if chat title doesn't match filter
        }
    }

    // Query Message Containers
    const messageElements = document.querySelectorAll('#main .focusable-list-item, #main [data-id]');
    let newMessages = [];

    messageElements.forEach((el) => {
        try {
            const dataId = el.getAttribute("data-id") || "";
            
            // Extract Message Text
            const textEl = el.querySelector(".copyable-text, .selectable-text");
            const messageText = textEl ? textEl.innerText.trim() : "";
            if (!messageText) return;

            // Extract Sender Info
            let senderName = "System/Me";
            let senderNumber = "";
            let msgTimestamp = new Date().toLocaleTimeString();

            // Try copyable-text metadata attribute
            const copyableEl = el.querySelector(".copyable-text");
            if (copyableEl) {
                const metaData = copyableEl.getAttribute("data-pre-plain-text");
                if (metaData) {
                    // Format: "[10:45 AM, 8/31/2026] Sender Name: "
                    const timeMatch = metaData.match(/\[(.*?)\]/);
                    if (timeMatch) msgTimestamp = timeMatch[1];
                    const nameMatch = metaData.match(/\]\s*([^:]+):/);
                    if (nameMatch) senderName = nameMatch[1].trim();
                }
            }

            // Create unique signature ID
            const signature = dataId || `${groupName}_${senderName}_${messageText}_${msgTimestamp}`;
            if (processedMessageIds.has(signature)) return;

            processedMessageIds.add(signature);
            newMessages.push({
                group_name: groupName,
                sender_name: senderName,
                sender_number: senderNumber,
                message_text: messageText,
                msg_timestamp: msgTimestamp
            });
        } catch (err) {
            console.error("[WhatsApp Scraper] Error parsing message element:", err);
        }
    });

    if (newMessages.length > 0) {
        console.log(`[WhatsApp Scraper] Scraped ${newMessages.length} new messages from "${groupName}"`);
        chrome.runtime.sendMessage({
            action: "INGEST_MESSAGES",
            payload: {
                messages: newMessages
            }
        });
    }

    return newMessages.length;
}
