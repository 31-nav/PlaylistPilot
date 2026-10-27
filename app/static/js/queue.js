/**
 * Queue Manager Logic
 */
document.addEventListener("DOMContentLoaded", () => {
  setupQueueControls();
  setupRowActions();

  window.addEventListener("queue-status-updated", (e) => {
    updateQueueScreen(e.detail);
  });
});

function setupQueueControls() {
  const btnStart = document.getElementById("btn-queue-start");
  const btnPause = document.getElementById("btn-queue-pause");
  const btnResume = document.getElementById("btn-queue-resume");
  const btnCancelAll = document.getElementById("btn-queue-cancel-all");
  const btnRetryAll = document.getElementById("btn-queue-retry-all");

  if (btnStart) {
    btnStart.addEventListener("click", async () => {
      try {
        btnStart.disabled = true;
        const res = await fetch("/api/queue/start", { method: "POST" });
        const data = await res.json();
        Notifications.success(data.message);
      } catch (e) {
        Notifications.error("Failed to start queue.");
      } finally {
        btnStart.disabled = false;
      }
    });
  }

  if (btnPause) {
    btnPause.addEventListener("click", async () => {
      try {
        btnPause.disabled = true;
        const res = await fetch("/api/queue/pause", { method: "POST" });
        const data = await res.json();
        Notifications.info(data.message);
      } catch (e) {
        Notifications.error("Failed to pause queue.");
      } finally {
        btnPause.disabled = false;
      }
    });
  }

  if (btnResume) {
    btnResume.addEventListener("click", async () => {
      try {
        btnResume.disabled = true;
        const res = await fetch("/api/queue/resume", { method: "POST" });
        const data = await res.json();
        Notifications.success(data.message);
      } catch (e) {
        Notifications.error("Failed to resume queue.");
      } finally {
        btnResume.disabled = false;
      }
    });
  }

  if (btnCancelAll) {
    btnCancelAll.addEventListener("click", async () => {
      if (!confirm("Are you sure you want to cancel all waiting jobs?")) return;
      try {
        btnCancelAll.disabled = true;
        const res = await fetch("/api/queue/cancel", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({})
        });
        const data = await res.json();
        Notifications.info(data.message);
        setTimeout(() => window.location.reload(), 600);
      } catch (e) {
        Notifications.error("Failed to cancel waiting jobs.");
      } finally {
        btnCancelAll.disabled = false;
      }
    });
  }

  if (btnRetryAll) {
    btnRetryAll.addEventListener("click", async () => {
      try {
        btnRetryAll.disabled = true;
        const res = await fetch("/api/queue/retry-all", { method: "POST" });
        const data = await res.json();
        Notifications.success(`Requeued ${data.retried_count} failed jobs.`);
        setTimeout(() => window.location.reload(), 600);
      } catch (e) {
        Notifications.error("Failed to retry jobs.");
      } finally {
        btnRetryAll.disabled = false;
      }
    });
  }
}

function setupRowActions() {
  document.addEventListener("click", async (e) => {
    // Prioritize Button
    const priBtn = e.target.closest(".btn-prioritize");
    if (priBtn) {
      const jobId = priBtn.getAttribute("data-job-id");
      try {
        priBtn.disabled = true;
        const res = await fetch(`/api/queue/${jobId}/prioritize`, { method: "POST" });
        const data = await res.json();
        if (data.success) {
          Notifications.success(data.message);
          setTimeout(() => window.location.reload(), 500);
        } else {
          Notifications.error(data.error);
        }
      } catch (err) {
        Notifications.error("Error prioritizing job.");
      } finally {
        priBtn.disabled = false;
      }
      return;
    }

    // Cancel Job Button
    const cancelBtn = e.target.closest(".btn-cancel-job");
    if (cancelBtn) {
      const jobId = cancelBtn.getAttribute("data-job-id");
      try {
        cancelBtn.disabled = true;
        const res = await fetch("/api/queue/cancel", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ job_id: parseInt(jobId) })
        });
        const data = await res.json();
        if (data.success) {
          Notifications.info(data.message);
          setTimeout(() => window.location.reload(), 500);
        } else {
          Notifications.error(data.error);
        }
      } catch (err) {
        Notifications.error("Error cancelling job.");
      } finally {
        cancelBtn.disabled = false;
      }
      return;
    }

    // Retry Job Button
    const retryBtn = e.target.closest(".btn-retry-job");
    if (retryBtn) {
      const jobId = retryBtn.getAttribute("data-job-id");
      try {
        retryBtn.disabled = true;
        const res = await fetch("/api/queue/retry", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ job_id: parseInt(jobId) })
        });
        const data = await res.json();
        if (data.success) {
          Notifications.success(data.message);
          setTimeout(() => window.location.reload(), 500);
        } else {
          Notifications.error(data.error);
        }
      } catch (err) {
        Notifications.error("Error retrying job.");
      } finally {
        retryBtn.disabled = false;
      }
      return;
    }
  });

  // Handle Quality Selection Change in Queue
  document.addEventListener("change", async (e) => {
    const sel = e.target.closest(".select-job-quality");
    if (sel) {
      const jobId = sel.getAttribute("data-job-id");
      const newQuality = sel.value;
      try {
        sel.disabled = true;
        const res = await fetch(`/api/queue/${jobId}/quality`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ quality: newQuality }),
        });
        const data = await res.json();
        if (data.success) {
          Notifications.success(`Job #${jobId} quality updated to ${newQuality.toUpperCase()}`);
        } else {
          Notifications.error(data.error || "Failed to update quality.");
        }
      } catch (err) {
        Notifications.error("Network error updating quality.");
      } finally {
        sel.disabled = false;
      }
    }
  });
}

function updateQueueScreen(data) {
  // Update overall progress bar
  const overallBar = document.getElementById("queue-overall-progress-fill");
  const overallPct = document.getElementById("queue-overall-progress-pct");
  if (overallBar) overallBar.style.width = `${data.overall_progress}%`;
  if (overallPct) overallPct.textContent = `${data.overall_progress}%`;

  // Update active job card
  const activeContainer = document.getElementById("active-job-container");
  const noActiveNotice = document.getElementById("no-active-job-notice");
  const activeTitle = document.getElementById("active-job-title");
  const activeProgressBar = document.getElementById("active-job-progress-fill");
  const activeProgressPct = document.getElementById("active-job-progress-pct");
  const activeStateBadge = document.getElementById("active-job-badge");

  if (data.active_job) {
    if (activeContainer) activeContainer.style.display = "block";
    if (noActiveNotice) noActiveNotice.style.display = "none";
    if (activeTitle && data.active_job.media_item) {
      activeTitle.textContent = `#${data.active_job.id} - ${data.active_job.media_item.title}`;
    }
    if (activeProgressBar) {
      activeProgressBar.style.width = `${data.active_job.progress_percent}%`;
    }
    if (activeProgressPct) {
      activeProgressPct.textContent = `${data.active_job.progress_percent}%`;
    }
    if (activeStateBadge) {
      activeStateBadge.className = "badge-status downloading";
      activeStateBadge.textContent = "Processing (Active)";
    }
  } else {
    if (activeContainer) activeContainer.style.display = "none";
    if (noActiveNotice) noActiveNotice.style.display = "block";
  }

  // Update button states
  const btnStart = document.getElementById("btn-queue-start");
  const btnPause = document.getElementById("btn-queue-pause");
  const btnResume = document.getElementById("btn-queue-resume");

  if (btnStart && btnPause && btnResume) {
    if (data.worker_running && !data.worker_paused) {
      btnStart.disabled = true;
      btnPause.disabled = false;
      btnResume.disabled = true;
    } else if (data.worker_paused) {
      btnStart.disabled = true;
      btnPause.disabled = true;
      btnResume.disabled = false;
    } else {
      btnStart.disabled = false;
      btnPause.disabled = true;
      btnResume.disabled = true;
    }
  }
}
