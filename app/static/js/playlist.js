/**
 * Playlist Explorer Logic
 */
document.addEventListener("DOMContentLoaded", () => {
  setupSelectionControls();
  setupQueueActions();
});

function setupSelectionControls() {
  const selectAllCheckbox = document.getElementById("select-all-items");
  const itemCheckboxes = document.querySelectorAll(".item-checkbox");
  const selectionCountBadge = document.getElementById("selection-count");
  const btnQueueSelected = document.getElementById("btn-queue-selected");

  function updateCount() {
    const checked = document.querySelectorAll(".item-checkbox:checked");
    const count = checked.length;
    if (selectionCountBadge) {
      selectionCountBadge.textContent = `${count} selected`;
      selectionCountBadge.style.display = count > 0 ? "inline-block" : "none";
    }
    if (btnQueueSelected) {
      btnQueueSelected.disabled = count === 0;
    }
  }

  if (selectAllCheckbox) {
    selectAllCheckbox.addEventListener("change", (e) => {
      itemCheckboxes.forEach((cb) => {
        cb.checked = e.target.checked;
      });
      updateCount();
    });
  }

  itemCheckboxes.forEach((cb) => {
    cb.addEventListener("change", () => {
      const allChecked = Array.from(itemCheckboxes).every((c) => c.checked);
      if (selectAllCheckbox) selectAllCheckbox.checked = allChecked;
      updateCount();
    });
  });

  const btnClearSelection = document.getElementById("btn-clear-selection");
  if (btnClearSelection) {
    btnClearSelection.addEventListener("click", () => {
      itemCheckboxes.forEach((cb) => (cb.checked = false));
      if (selectAllCheckbox) selectAllCheckbox.checked = false;
      updateCount();
    });
  }
}

function setupQueueActions() {
  const btnQueueSelected = document.getElementById("btn-queue-selected");
  if (btnQueueSelected) {
    btnQueueSelected.addEventListener("click", async () => {
      const checked = document.querySelectorAll(".item-checkbox:checked");
      const ids = Array.from(checked).map((cb) => parseInt(cb.value));

      if (ids.length === 0) {
        Notifications.error("No items selected.");
        return;
      }

      try {
        btnQueueSelected.disabled = true;
        btnQueueSelected.textContent = "Adding...";
        const qualityEl = document.getElementById("select-download-quality");
        const qualityVal = qualityEl ? qualityEl.value : "best";
        const jobType = qualityVal === "audio_mp3" ? "youtube_audio" : "youtube_download";

        const res = await fetch("/api/queue", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ item_ids: ids, quality: qualityVal, job_type: jobType })
        });
        const data = await res.json();
        if (data.success) {
          Notifications.success(data.message);
          setTimeout(() => window.location.href = "/queue", 1000);
        } else {
          Notifications.error(data.error || "Failed to add items to queue.");
        }
      } catch (err) {
        Notifications.error("Network error enqueueing items.");
      } finally {
        btnQueueSelected.disabled = false;
        btnQueueSelected.textContent = "Add Selected to Queue";
      }
    });
  }

  const btnQueueAll = document.getElementById("btn-queue-all");
  if (btnQueueAll) {
    btnQueueAll.addEventListener("click", async () => {
      const playlistId = btnQueueAll.getAttribute("data-playlist-id");
      if (!playlistId) return;

      if (!confirm("Are you sure you want to add all eligible playlist items to the queue?")) {
        return;
      }

      try {
        btnQueueAll.disabled = true;
        btnQueueAll.textContent = "Fetching all items...";
        const qualityEl = document.getElementById("select-download-quality");
        const qualityVal = qualityEl ? qualityEl.value : "best";
        const jobType = qualityVal === "audio_mp3" ? "youtube_audio" : "youtube_download";
        
        // Fetch all items for this playlist
        const res = await fetch(`/api/playlists/${playlistId}/items?per_page=500`);
        const data = await res.json();
        if (data.success && data.items) {
          const ids = data.items.map((it) => it.id);
          const qRes = await fetch("/api/queue", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ item_ids: ids, quality: qualityVal, job_type: jobType })
          });
          const qData = await qRes.json();
          if (qData.success) {
            Notifications.success(qData.message);
            setTimeout(() => window.location.href = "/queue", 1000);
          } else {
            Notifications.error(qData.error || "Error adding items.");
          }
        }
      } catch (err) {
        Notifications.error("Error enqueueing playlist items.");
      } finally {
        btnQueueAll.disabled = false;
        btnQueueAll.textContent = "Add All Items to Queue";
      }
    });
  }
}
