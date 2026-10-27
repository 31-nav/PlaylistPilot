/**
 * History Page Logic
 */
document.addEventListener("DOMContentLoaded", () => {
  setupHistoryFilters();
  setupHistoryRowActions();
});

function setupHistoryFilters() {
  const statusFilter = document.getElementById("history-status-filter");
  if (statusFilter) {
    statusFilter.addEventListener("change", () => {
      document.getElementById("history-filter-form").submit();
    });
  }
}

function setupHistoryRowActions() {
  document.addEventListener("click", async (e) => {
    const retryBtn = e.target.closest(".btn-history-retry");
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
          setTimeout(() => window.location.reload(), 600);
        } else {
          Notifications.error(data.error);
        }
      } catch (err) {
        Notifications.error("Error retrying job.");
      } finally {
        retryBtn.disabled = false;
      }
    }
  });
}
