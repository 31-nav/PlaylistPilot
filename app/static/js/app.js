/**
 * PlaylistPilot Global Application Engine
 */
document.addEventListener("DOMContentLoaded", () => {
  Notifications.init();
  setupSimulationControls();
  startStatusPolling();
});

let isNetworkOffline = false;

function setupSimulationControls() {
  const simNetworkBtn = document.getElementById("btn-sim-network");
  if (simNetworkBtn) {
    simNetworkBtn.addEventListener("click", async () => {
      try {
        simNetworkBtn.disabled = true;
        const res = await fetch("/api/simulate/network", {
          method: "POST",
          headers: { "Content-Type": "application/json" }
        });
        const data = await res.json();
        if (data.success) {
          isNetworkOffline = data.simulated_network_offline;
          updateNetworkUI(isNetworkOffline);
          Notifications.show(data.message, isNetworkOffline ? "error" : "success");
        }
      } catch (err) {
        Notifications.error("Failed to toggle simulated network.");
      } finally {
        simNetworkBtn.disabled = false;
      }
    });
  }

  const simFailBtn = document.getElementById("btn-sim-fail");
  if (simFailBtn) {
    simFailBtn.addEventListener("click", async () => {
      try {
        simFailBtn.disabled = true;
        const res = await fetch("/api/simulate/fail-next", {
          method: "POST",
          headers: { "Content-Type": "application/json" }
        });
        const data = await res.json();
        if (data.success) {
          Notifications.show(data.message, "info");
        }
      } catch (err) {
        Notifications.error("Failed to inject simulation failure.");
      } finally {
        simFailBtn.disabled = false;
      }
    });
  }
}

function updateNetworkUI(offline) {
  const pill = document.getElementById("header-network-pill");
  const netText = document.getElementById("header-network-text");
  const simBtnText = document.getElementById("sim-network-btn-text");

  if (pill && netText) {
    if (offline) {
      pill.classList.add("offline");
      netText.textContent = "Offline (Simulated)";
      if (simBtnText) simBtnText.textContent = "Restore Simulated Network";
    } else {
      pill.classList.remove("offline");
      netText.textContent = "Online";
      if (simBtnText) simBtnText.textContent = "Simulate Network Drop";
    }
  }
}

let pollTimer = null;
function startStatusPolling() {
  const poll = async () => {
    try {
      const res = await fetch("/api/queue/status");
      if (res.ok) {
        const data = await res.json();
        if (data.success) {
          updateHeaderQueueStatus(data);
          // If queue page or dashboard has defined a listener, dispatch event
          window.dispatchEvent(new CustomEvent("queue-status-updated", { detail: data }));
        }
      }
    } catch (e) {
      // Ignore background fetch error
    }
  };

  poll();
  pollTimer = setInterval(poll, 2000);
}

function updateHeaderQueueStatus(data) {
  const badge = document.getElementById("header-queue-badge");
  const statusPill = document.getElementById("header-queue-status-pill");
  const queueNavBadge = document.getElementById("sidebar-queue-count");

  if (queueNavBadge) {
    const waiting = data.counts.queued || 0;
    queueNavBadge.textContent = waiting;
    queueNavBadge.style.display = waiting > 0 ? "inline-block" : "none";
  }

  if (statusPill && badge) {
    if (data.counts.downloading > 0) {
      statusPill.className = "header-status-pill active";
      badge.textContent = `Processing (${data.overall_progress}%)`;
    } else if (data.worker_paused) {
      statusPill.className = "header-status-pill";
      badge.textContent = "Paused";
    } else if (data.counts.queued > 0) {
      statusPill.className = "header-status-pill";
      badge.textContent = `Waiting (${data.counts.queued})`;
    } else {
      statusPill.className = "header-status-pill";
      badge.textContent = "Idle";
    }
  }

  if (data.network_offline !== undefined && data.network_offline !== isNetworkOffline) {
    isNetworkOffline = data.network_offline;
    updateNetworkUI(isNetworkOffline);
  }
}
