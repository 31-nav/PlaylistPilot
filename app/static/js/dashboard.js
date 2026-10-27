/**
 * PlaylistPilot — Public YouTube Video & Playlist Downloader Frontend Logic
 * Supports pasting links, previewing video lists, selecting items (1, 3, 4, 7, etc.),
 * and step-by-step sequential downloading with direct saving to local device.
 */

document.addEventListener("DOMContentLoaded", () => {
  initPublicDownloader();
});

function initPublicDownloader() {
  const formFetch = document.getElementById("form-fetch-youtube");
  const inputUrl = document.getElementById("input-youtube-url");
  const btnPaste = document.getElementById("btn-paste-clipboard");
  const btnFetch = document.getElementById("btn-fetch-submit");
  const loadingState = document.getElementById("fetch-loading-state");
  const loadedSection = document.getElementById("loaded-content-section");

  // Summary elements
  const summaryThumb = document.getElementById("summary-thumb");
  const summaryTitle = document.getElementById("summary-title");
  const summaryChannel = document.getElementById("summary-channel");
  const summaryCountBadge = document.getElementById("summary-count-badge");

  // Toolbar & actions
  const btnSelectAll = document.getElementById("btn-select-all");
  const btnDeselectAll = document.getElementById("btn-deselect-all");
  const selectionBadge = document.getElementById("selection-count-badge");
  const qualitySelect = document.getElementById("batch-quality-select");
  const btnDownloadSelected = document.getElementById("btn-download-selected");
  const btnDownloadSelectedText = document.getElementById("btn-download-selected-text");

  // Batch Monitor
  const batchCenter = document.getElementById("batch-download-center");
  const batchStepCounter = document.getElementById("batch-step-counter");
  const batchActiveTitle = document.getElementById("batch-active-title");
  const batchActiveStatus = document.getElementById("batch-active-status");
  const batchActiveFill = document.getElementById("batch-active-fill");
  const batchActivePct = document.getElementById("batch-active-pct");

  // Video list container
  const videoItemsList = document.getElementById("video-items-list");

  // State
  let loadedItems = [];
  let isProcessingBatch = false;

  // 1. Paste from clipboard button
  if (btnPaste && inputUrl) {
    btnPaste.addEventListener("click", async () => {
      try {
        if (navigator.clipboard && navigator.clipboard.readText) {
          const text = await navigator.clipboard.readText();
          if (text) {
            inputUrl.value = text.trim();
            Notifications.info("Link pasted from clipboard!");
            inputUrl.focus();
          }
        } else {
          inputUrl.focus();
          Notifications.info("Press Ctrl+V to paste YouTube link.");
        }
      } catch (err) {
        inputUrl.focus();
      }
    });
  }

  // 2. Fetch Form Submission
  if (formFetch) {
    formFetch.addEventListener("submit", async (e) => {
      e.preventDefault();
      const url = inputUrl.value.trim();

      if (!url) {
        Notifications.error("Please paste a valid YouTube video or playlist link.");
        inputUrl.focus();
        return;
      }

      try {
        btnFetch.disabled = true;
        loadingState.style.display = "block";
        loadedSection.style.display = "none";
        batchCenter.style.display = "none";
        loadingState.scrollIntoView({ behavior: "smooth", block: "nearest" });

        const res = await fetch("/api/fetch", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url }),
        });

        const data = await res.json();

        if (!data.success) {
          Notifications.error(data.error || "Failed to retrieve YouTube link details.");
          return;
        }

        // Render loaded content
        loadedItems = data.items || [];
        summaryTitle.textContent = data.title || "YouTube Videos";
        if (data.thumbnail_url) summaryThumb.src = data.thumbnail_url;
        summaryChannel.textContent = data.uploader || "YouTube";
        summaryCountBadge.textContent = `${loadedItems.length} Video${loadedItems.length === 1 ? '' : 's'} Found`;

        renderVideoRows(loadedItems);
        updateSelectionState();

        loadedSection.style.display = "block";
        loadedSection.scrollIntoView({ behavior: "smooth", block: "start" });
        Notifications.success(`Loaded ${loadedItems.length} video(s)! Pick the ones you want to download.`);

      } catch (err) {
        Notifications.error("Network error while connecting to YouTube service.");
      } finally {
        btnFetch.disabled = false;
        loadingState.style.display = "none";
      }
    });
  }

  // 3. Render video items rows
  function renderVideoRows(items) {
    videoItemsList.innerHTML = "";

    items.forEach((item, index) => {
      const row = document.createElement("div");
      row.className = "video-select-row selected";
      row.setAttribute("data-video-id", item.id);
      row.setAttribute("data-video-idx", index);

      row.innerHTML = `
        <div class="video-checkbox-wrapper">
          <input type="checkbox" class="custom-checkbox video-item-chk" checked data-video-id="${item.id}">
        </div>
        <div class="video-idx-badge">#${item.index || (index + 1)}</div>
        <div class="video-thumb-container">
          <img src="${item.thumbnail_url}" alt="Thumb" class="video-thumb-img" loading="lazy">
          <div class="video-duration-tag">${item.duration_formatted || '--:--'}</div>
        </div>
        <div class="video-info-area">
          <div class="video-row-title" title="${escapeHtml(item.title)}">${escapeHtml(item.title)}</div>
          <div class="video-row-meta">${escapeHtml(item.uploader || 'YouTube')}</div>
        </div>
        <div class="video-row-actions">
          <span class="badge-status queued row-status-badge" style="font-size: 0.72rem;">Ready</span>
          <button type="button" class="btn-3d btn-3d-secondary btn-3d-sm btn-single-download" data-video-id="${item.id}" title="Download this video directly">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
            <span>Download</span>
          </button>
        </div>
      `;

      // Row click toggles checkbox
      row.addEventListener("click", (e) => {
        if (e.target.closest(".btn-single-download")) return;
        if (e.target.tagName !== "INPUT") {
          const chk = row.querySelector(".video-item-chk");
          chk.checked = !chk.checked;
        }
        if (row.querySelector(".video-item-chk").checked) {
          row.classList.add("selected");
        } else {
          row.classList.remove("selected");
        }
        updateSelectionState();
      });

      // Individual download button
      const singleDlBtn = row.querySelector(".btn-single-download");
      singleDlBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        downloadSingleVideo(item);
      });

      videoItemsList.appendChild(row);
    });
  }

  // 4. Update Selection State & Counter
  function updateSelectionState() {
    const checkboxes = document.querySelectorAll(".video-item-chk");
    const checkedCount = Array.from(checkboxes).filter(c => c.checked).length;
    const totalCount = checkboxes.length;

    selectionBadge.textContent = `Selected: ${checkedCount} of ${totalCount} videos`;
    btnDownloadSelectedText.textContent = `Download Selected (${checkedCount}) to Device`;

    if (checkedCount === 0) {
      btnDownloadSelected.disabled = true;
      btnDownloadSelected.style.opacity = "0.5";
    } else {
      btnDownloadSelected.disabled = false;
      btnDownloadSelected.style.opacity = "1";
    }
  }

  // Select All / Deselect All
  if (btnSelectAll) {
    btnSelectAll.addEventListener("click", () => {
      document.querySelectorAll(".video-item-chk").forEach(c => {
        c.checked = true;
        c.closest(".video-select-row").classList.add("selected");
      });
      updateSelectionState();
    });
  }

  if (btnDeselectAll) {
    btnDeselectAll.addEventListener("click", () => {
      document.querySelectorAll(".video-item-chk").forEach(c => {
        c.checked = false;
        c.closest(".video-select-row").classList.remove("selected");
      });
      updateSelectionState();
    });
  }

  // 5. Batch Download Execution (Step-by-Step with local file save)
  if (btnDownloadSelected) {
    btnDownloadSelected.addEventListener("click", async () => {
      if (isProcessingBatch) return;

      const checkedBoxes = Array.from(document.querySelectorAll(".video-item-chk:checked"));
      if (checkedBoxes.length === 0) {
        Notifications.error("Please select at least 1 video to download.");
        return;
      }

      const selectedIds = new Set(checkedBoxes.map(c => c.getAttribute("data-video-id")));
      const selectedItems = loadedItems.filter(item => selectedIds.has(item.id));
      const quality = qualitySelect ? qualitySelect.value : "best";

      try {
        isProcessingBatch = true;
        btnDownloadSelected.disabled = true;
        batchCenter.style.display = "block";
        batchCenter.scrollIntoView({ behavior: "smooth", block: "nearest" });

        batchActiveTitle.textContent = "Starting queue...";
        batchStepCounter.textContent = `0 of ${selectedItems.length}`;
        batchActiveFill.style.width = "0%";
        batchActivePct.textContent = "0%";

        const res = await fetch("/api/batch-download", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ items: selectedItems, quality }),
        });

        const data = await res.json();
        if (!data.success || !data.jobs) {
          Notifications.error(data.error || "Failed to start batch download.");
          isProcessingBatch = false;
          btnDownloadSelected.disabled = false;
          return;
        }

        Notifications.info(`Queue initialized with ${data.jobs.length} video(s). Downloading step-by-step...`);

        // Execute sequential job monitor
        await processJobsSequentially(data.jobs);

      } catch (err) {
        Notifications.error("Error communicating with download engine.");
      } finally {
        isProcessingBatch = false;
        btnDownloadSelected.disabled = false;
      }
    });
  }

  // 6. Sequential Step-by-Step Processor & Local Auto-Save
  async function processJobsSequentially(jobs) {
    for (let i = 0; i < jobs.length; i++) {
      const jobInfo = jobs[i];
      const videoRow = document.querySelector(`.video-select-row[data-video-id="${jobInfo.video_id}"]`);
      const statusBadge = videoRow ? videoRow.querySelector(".row-status-badge") : null;

      batchStepCounter.textContent = `Video ${i + 1} of ${jobs.length}`;
      batchActiveTitle.textContent = jobInfo.title;
      batchActiveStatus.textContent = `Processing video ${i + 1} of ${jobs.length}...`;
      batchActiveFill.style.width = "0%";
      batchActivePct.textContent = "0%";

      if (statusBadge) {
        statusBadge.className = "badge-status downloading row-status-badge";
        statusBadge.textContent = "Downloading...";
      }

      // Poll until this specific job completes
      const completedJob = await pollSingleJobUntilFinished(jobInfo.job_id);

      if (completedJob && completedJob.status === "completed") {
        batchActiveFill.style.width = "100%";
        batchActivePct.textContent = "100%";

        const dlUrl = completedJob.download_url || `/api/jobs/${completedJob.id}/download`;

        // Automatically trigger browser download straight into local Downloads folder!
        triggerLocalBrowserDownload(dlUrl);

        if (statusBadge) {
          statusBadge.className = "badge-status completed row-status-badge";
          statusBadge.textContent = "Saved to Downloads";
        }

        if (videoRow) {
          // Provide direct save button in row
          const actionArea = videoRow.querySelector(".video-row-actions");
          actionArea.innerHTML = `
            <span class="badge-status completed" style="font-size: 0.72rem;">Saved to Downloads</span>
            <a href="${dlUrl}" class="btn-3d btn-3d-primary btn-3d-sm" download style="text-decoration: none; padding: 4px 8px; font-size: 0.75rem;">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
              <span>Save File</span>
            </a>
          `;
        }

        Notifications.success(`Saved: ${jobInfo.title} to your Downloads folder!`);
      } else {
        if (statusBadge) {
          statusBadge.className = "badge-status failed row-status-badge";
          statusBadge.textContent = "Failed";
        }
        Notifications.error(`Download error for: ${jobInfo.title}`);
      }
    }

    // All jobs finished
    batchActiveTitle.textContent = "Batch Download Completed!";
    batchActiveStatus.textContent = `All ${jobs.length} selected videos downloaded directly to your device.`;
    batchActiveFill.style.width = "100%";
    batchActivePct.textContent = "100%";
    Notifications.success(`All ${jobs.length} files saved directly to your local device!`);
  }

  // 7. Polling single job until completion
  function pollSingleJobUntilFinished(jobId) {
    return new Promise((resolve) => {
      let tries = 0;
      const interval = setInterval(async () => {
        tries++;
        try {
          const res = await fetch(`/api/jobs/${jobId}`);
          const data = await res.json();
          if (data.success && data.job) {
            const j = data.job;
            const pct = Math.max(0, Math.min(100, Math.round(j.progress_percent || 0)));
            batchActiveFill.style.width = `${pct}%`;
            batchActivePct.textContent = `${pct}%`;

            if (j.status === "completed" || j.status === "failed" || j.status === "cancelled") {
              clearInterval(interval);
              resolve(j);
            }
          }
        } catch (e) {
          // Keep polling on transient errors
        }

        // Safety timeout (15 minutes per video)
        if (tries > 900) {
          clearInterval(interval);
          resolve(null);
        }
      }, 750);
    });
  }

  // 8. Single video download from row
  async function downloadSingleVideo(item) {
    const quality = qualitySelect ? qualitySelect.value : "best";
    Notifications.info(`Starting download for '${item.title}'...`);
    
    // Use batch runner with single item
    batchCenter.style.display = "block";
    batchCenter.scrollIntoView({ behavior: "smooth", block: "nearest" });
    
    const res = await fetch("/api/batch-download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ items: [item], quality }),
    });

    const data = await res.json();
    if (data.success && data.jobs) {
      await processJobsSequentially(data.jobs);
    } else {
      Notifications.error("Could not start download.");
    }
  }

  // 9. Programmatic browser download trigger
  function triggerLocalBrowserDownload(url) {
    try {
      const a = document.createElement("a");
      a.href = url;
      a.download = "";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    } catch (e) {
      console.warn("Direct download popup blocked by browser. Direct save buttons remain available.");
    }
  }

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text || "";
    return div.innerHTML;
  }
}
