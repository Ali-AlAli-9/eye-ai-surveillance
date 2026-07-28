let ws = null;
let reconnectTimer = null;
let reconnectDelay = 1000;
const MAX_RECONNECT_DELAY = 30000;
let lastFrameTime = 0;

const ENGINE_URLS = {
    start: document.querySelector('[data-engine-start]')?.dataset.engineStart || "/engine/start/",
    stop: document.querySelector('[data-engine-stop]')?.dataset.engineStop || "/engine/stop/"
};

function connectWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = protocol + "//" + window.location.host + "/ws/stream/";
    ws = new WebSocket(wsUrl);

    ws.onopen = function() {
        reconnectDelay = 1000;
        if (reconnectTimer) {
            clearTimeout(reconnectTimer);
            reconnectTimer = null;
        }
        updateStatus("waiting");
    };

    ws.onmessage = function(event) {
        try {
            const data = JSON.parse(event.data);

            if (data.type === "status") {
                if (data.running) {
                    showEngineRunning();
                    updateStatus("waiting");
                    updateEngineUI(true);
                } else {
                    updateStatus("engine_off");
                    updateEngineUI(false);
                }
                return;
            }

            const img = document.getElementById("liveStream");
            if (img && data.image) {
                img.src = "data:image/jpeg;base64," + data.image;
                lastFrameTime = Date.now();
                updateStatus("connected");
                showImage(true);
            }

            let personCount = 0;
            if (data.detections) {
                personCount = data.detections.filter(d => d.class === "person").length;
            }
            updatePersonCount(personCount);
            updateStreamTime();
        } catch (e) {
            console.error("WebSocket message parse error:", e);
        }
    };

    ws.onclose = function() {
        updateStatus("disconnected");
        ws = null;
        reconnectTimer = setTimeout(connectWebSocket, reconnectDelay);
        reconnectDelay = Math.min(reconnectDelay * 2, MAX_RECONNECT_DELAY);
    };

    ws.onerror = function() {
        ws.close();
    };
}

function updateStatus(status) {
    const el = document.getElementById("streamStatus");
    if (!el) return;
    switch (status) {
        case "connected":
            el.className = "badge bg-success";
            el.textContent = "\u25CF \u0645\u062A\u0635\u0644";
            break;
        case "waiting":
            el.className = "badge bg-warning";
            el.textContent = "\u25CF \u062C\u0627\u0631\u064D \u0627\u0644\u0627\u062A\u0635\u0627\u0644...";
            break;
        case "engine_off":
            el.className = "badge bg-danger";
            el.textContent = "\u25CF \u0627\u0644\u0645\u062D\u0631\u0643 \u0645\u062A\u0648\u0642\u0641";
            break;
        case "disconnected":
            el.className = "badge bg-danger";
            el.textContent = "\u25CF \u063A\u064A\u0631 \u0645\u062A\u0635\u0644";
            break;
    }
}

function updateEngineUI(running) {
    var control = document.getElementById("engineControl");
    var badge = document.getElementById("engineStatusBadge");
    if (!control) return;

    var form = control.querySelector("form");
    var btn = document.getElementById("engineBtn");
    if (!form || !btn) return;

    if (running) {
        form.action = ENGINE_URLS.stop;
        form.method = "post";
        btn.className = "btn-custom btn-custom-danger";
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-stop"></i> \u0625\u064A\u0642\u0627\u0641 \u0627\u0644\u0643\u0627\u0645\u064A\u0631\u0627';
        if (badge) {
            badge.className = "engine-status engine-status-on";
            badge.innerHTML = '<i class="fas fa-circle"></i> \u064A\u0639\u0645\u0644 \u0627\u0644\u0622\u0646';
        }
    } else {
        form.action = ENGINE_URLS.start;
        form.method = "post";
        btn.className = "btn-custom btn-custom-success";
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-play"></i> \u062A\u0634\u063A\u064A\u0644 \u0627\u0644\u0643\u0627\u0645\u064A\u0631\u0627';
        if (badge) {
            badge.className = "engine-status engine-status-off";
            badge.innerHTML = '<i class="fas fa-circle"></i> \u0645\u062A\u0648\u0642\u0641';
        }
    }
}

function showImage(hasImage) {
    const img = document.getElementById("liveStream");
    const placeholder = document.getElementById("streamPlaceholder");
    if (img) img.style.display = hasImage ? "block" : "none";
    if (placeholder) placeholder.style.display = hasImage ? "none" : "flex";
}

function hideLoadingBanner() {
    var banner = document.getElementById("engineLoading");
    if (banner) banner.style.display = "none";
}

function showEngineRunning() {
    var loading = document.getElementById("engineLoading");
    var form = document.getElementById("engineForm");
    var badge = document.getElementById("engineStatusBadge");
    if (loading) loading.style.display = "none";
    if (form) form.style.display = "block";
    if (badge) badge.style.display = "inline";
}

function updatePersonCount(count) {
    const el = document.getElementById("personCount");
    if (el) el.textContent = count;
}

function updateStreamTime() {
    const el = document.getElementById("streamTime");
    if (!el) return;
    const now = new Date();
    el.textContent = now.toLocaleTimeString("ar-SA", {hour12: false});
}

setInterval(function() {
    if (lastFrameTime === 0) return;
    const elapsed = (Date.now() - lastFrameTime) / 1000;
    if (elapsed > 5) {
        updateStatus("waiting");
        showImage(false);
    }
}, 3000);

connectWebSocket();
