(() => {
  const uploadForm = document.getElementById("upload-form");
  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("files");
  const uploadStatusText = document.getElementById("upload-status-text");
  const uploadProgress = document.getElementById("upload-progress");
  const progressShell = document.querySelector(".progress-shell");
  let droppedFiles = null;
  let uploadInFlight = false;

  const setUploadStatus = (message, percent = null) => {
    if (uploadStatusText) {
      uploadStatusText.textContent = message;
    }
    if (uploadProgress && percent != null) {
      const clamped = Math.max(0, Math.min(100, Math.round(percent)));
      uploadProgress.style.width = `${clamped}%`;
      if (progressShell) {
        progressShell.setAttribute("aria-valuenow", String(clamped));
      }
    }
  };

  const getSelectedFiles = () => {
    return fileInput?.files && fileInput.files.length ? fileInput.files : droppedFiles;
  };

  const updateQueuedCount = (selectedOverride = null) => {
    const selected = selectedOverride || getSelectedFiles();
    const count = selected?.length || 0;
    if (!count) {
      setUploadStatus("No files selected.", 0);
      return;
    }
    const noun = count === 1 ? "file" : "files";
    setUploadStatus(`${count} ${noun} ready to upload.`, 0);
  };

  const startUpload = (selected) => {
    const files = Array.from(selected || []);
    if (!files.length) {
      setUploadStatus("Choose at least one image before uploading.", 0);
      return;
    }
    if (uploadInFlight) {
      setUploadStatus("Upload already in progress...", null);
      return;
    }

    uploadInFlight = true;
    setUploadStatus("Preparing upload...", 1);

    const formData = new FormData();
    files.forEach((file) => formData.append("files", file, file.name));

    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/upload", true);

    xhr.upload.onprogress = (event) => {
      if (!event.lengthComputable) return;
      const percent = (event.loaded / event.total) * 100;
      setUploadStatus(`Uploading... ${Math.round(percent)}%`, percent);
    };

    xhr.onload = () => {
      uploadInFlight = false;
      if (xhr.status >= 200 && xhr.status < 400) {
        setUploadStatus("Upload complete. Redirecting...", 100);
        // Always go to crop queue after successful upload.
        window.location.href = "/crop";
        return;
      }
      const detail = xhr.responseText ? ` ${xhr.responseText.slice(0, 120)}` : "";
      setUploadStatus(`Upload failed (HTTP ${xhr.status}).${detail}`, 0);
    };

    xhr.onerror = () => {
      uploadInFlight = false;
      setUploadStatus("Upload failed due to a network error.", 0);
    };

    xhr.send(formData);
  };

  if (dropzone && fileInput) {
    const activate = (on) => dropzone.classList.toggle("active", on);

    ["dragenter", "dragover"].forEach((evt) => {
      dropzone.addEventListener(evt, (e) => {
        e.preventDefault();
        activate(true);
      });
    });

    ["dragleave", "drop"].forEach((evt) => {
      dropzone.addEventListener(evt, (e) => {
        e.preventDefault();
        activate(false);
      });
    });

    dropzone.addEventListener("drop", (e) => {
      if (!e.dataTransfer?.files?.length) return;
      droppedFiles = e.dataTransfer.files;
      try {
        fileInput.files = droppedFiles;
      } catch (_err) {
        // Some browsers block assigning to input.files; submit handler uses droppedFiles.
      }
      updateQueuedCount(droppedFiles);
      startUpload(droppedFiles);
    });
  }

  if (uploadForm && fileInput) {
    fileInput.addEventListener("change", () => {
      if (fileInput.files && fileInput.files.length) {
        droppedFiles = null;
      }
      const selected = getSelectedFiles();
      updateQueuedCount(selected);
      startUpload(selected);
    });

    uploadForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const selected = getSelectedFiles();
      startUpload(selected);
    });

    updateQueuedCount();
  }

  const list = document.getElementById("image-list");
  if (!list) return;

  let dragging = null;
  let lastEnteredCard = null;

  const syncOrder = async () => {
    const ids = [...list.querySelectorAll(".image-card")].map((el) => el.dataset.id);
    await fetch("/reorder", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ids }),
    });
  };

  const wouldMove = (target) => {
    if (!dragging || !target || target === dragging) return false;
    const children = [...list.querySelectorAll(".image-card")];
    const draggingIndex = children.indexOf(dragging);
    const targetIndex = children.indexOf(target);
    if (draggingIndex === -1 || targetIndex === -1) return false;

    if (draggingIndex < targetIndex) {
      return dragging.nextSibling !== target.nextSibling;
    }
    return dragging.nextSibling !== target;
  };

  const moveDraggingToTarget = (target) => {
    const children = [...list.querySelectorAll(".image-card")];
    const draggingIndex = children.indexOf(dragging);
    const targetIndex = children.indexOf(target);

    if (draggingIndex < targetIndex) {
      list.insertBefore(dragging, target.nextSibling);
      return;
    }
    list.insertBefore(dragging, target);
  };

  const animateReorder = (mutate) => {
    const cards = [...list.querySelectorAll(".image-card")];
    const firstRects = new Map(cards.map((card) => [card, card.getBoundingClientRect()]));
    mutate();
    const lastRects = new Map(cards.map((card) => [card, card.getBoundingClientRect()]));

    cards.forEach((card) => {
      const first = firstRects.get(card);
      const last = lastRects.get(card);
      if (!first || !last) return;

      const dx = first.left - last.left;
      const dy = first.top - last.top;
      if (Math.abs(dx) < 1 && Math.abs(dy) < 1) return;

      card.style.transition = "none";
      card.style.transform = `translate(${dx}px, ${dy}px)`;
      card.getBoundingClientRect();
      card.style.transition = "transform 180ms ease";
      card.style.transform = "";

      const cleanup = () => {
        card.style.transition = "";
        card.removeEventListener("transitionend", cleanup);
      };
      card.addEventListener("transitionend", cleanup);
    });
  };

  list.querySelectorAll(".image-card").forEach((card) => {
    card.addEventListener("dragstart", (e) => {
      dragging = card;
      lastEnteredCard = null;
      card.classList.add("dragging");

      if (e.dataTransfer) {
        e.dataTransfer.effectAllowed = "move";
        e.dataTransfer.setData("text/plain", card.dataset.id || "");
      }
    });

    card.addEventListener("dragend", async () => {
      card.classList.remove("dragging");
      dragging = null;
      lastEnteredCard = null;
      await syncOrder();
    });

    card.addEventListener("dragenter", (e) => {
      e.preventDefault();
      if (!dragging || card === dragging) return;
      if (lastEnteredCard === card) return;
      if (!wouldMove(card)) return;

      lastEnteredCard = card;
      animateReorder(() => moveDraggingToTarget(card));
    });
  });

  list.addEventListener("dragover", (e) => {
    e.preventDefault();
  });
})();
