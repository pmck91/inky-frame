(() => {
  const root = document.getElementById("crop-editor");
  if (!root) return;

  const imageId = root.dataset.imageId;
  const imageSrc = root.dataset.imageSrc;

  const canvas = document.getElementById("crop-canvas");
  const ctx = canvas.getContext("2d");

  const modeInput = document.getElementById("mode");
  const zoomInput = document.getElementById("zoom");
  const offsetXInput = document.getElementById("offset-x");
  const offsetYInput = document.getElementById("offset-y");
  const rotateLeftButton = document.getElementById("rotate-left");
  const rotateRightButton = document.getElementById("rotate-right");
  const flipXButton = document.getElementById("flip-x");
  const flipYButton = document.getElementById("flip-y");
  const resetButton = document.getElementById("reset-view");
  const saveButton = document.getElementById("save-crop");

  const TARGET_W = Number(root.dataset.displayWidth || canvas.width);
  const TARGET_H = Number(root.dataset.displayHeight || canvas.height);

  canvas.width = TARGET_W;
  canvas.height = TARGET_H;

  const image = new Image();
  image.decoding = "async";

  let baseScale = 1;
  let rotation = 0;
  let flipX = 1;
  let flipY = 1;

  const pointers = new Map();
  let panStart = null;
  let pinchStart = null;

  const clamp = (value, min, max) => Math.max(min, Math.min(max, value));

  const maxOffsetX = Math.max(200, Math.round(TARGET_W * 1.5));
  const maxOffsetY = Math.max(200, Math.round(TARGET_H * 1.5));
  offsetXInput.min = String(-maxOffsetX);
  offsetXInput.max = String(maxOffsetX);
  offsetYInput.min = String(-maxOffsetY);
  offsetYInput.max = String(maxOffsetY);

  const getZoomScale = () => Number(zoomInput.value) / 100;
  const getScale = () => baseScale * getZoomScale();
  const getOffsetX = () => Number(offsetXInput.value);
  const getOffsetY = () => Number(offsetYInput.value);

  const isQuarterTurn = () => Math.abs(rotation % 180) === 90;

  const getEffectiveSize = () => {
    if (isQuarterTurn()) {
      return { width: image.height, height: image.width };
    }
    return { width: image.width, height: image.height };
  };

  const computeBaseScale = () => {
    const cover = modeInput.value === "cover";
    const effective = getEffectiveSize();
    const widthScale = TARGET_W / effective.width;
    const heightScale = TARGET_H / effective.height;
    return cover ? Math.max(widthScale, heightScale) : Math.min(widthScale, heightScale);
  };

  const render = () => {
    if (!image.width || !image.height) return;

    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, TARGET_W, TARGET_H);

    const scale = getScale();
    const drawW = image.width * scale;
    const drawH = image.height * scale;

    ctx.save();
    ctx.translate(TARGET_W / 2 + getOffsetX(), TARGET_H / 2 + getOffsetY());
    ctx.rotate((rotation * Math.PI) / 180);
    ctx.scale(flipX, flipY);
    ctx.drawImage(image, -drawW / 2, -drawH / 2, drawW, drawH);
    ctx.restore();
  };

  const updateFlipButtons = () => {
    flipXButton.classList.toggle("active", flipX === -1);
    flipYButton.classList.toggle("active", flipY === -1);
  };

  const resetView = () => {
    baseScale = computeBaseScale();
    zoomInput.value = "100";
    offsetXInput.value = "0";
    offsetYInput.value = "0";
    rotation = 0;
    flipX = 1;
    flipY = 1;
    updateFlipButtons();
    render();
  };

  const zoomBy = (delta, centerX, centerY) => {
    const prevZoom = Number(zoomInput.value);
    const nextZoom = clamp(prevZoom + delta, 50, 300);
    if (nextZoom === prevZoom) return;

    const zoomFactor = nextZoom / prevZoom;
    const currentOffsetX = getOffsetX();
    const currentOffsetY = getOffsetY();

    const relX = centerX - TARGET_W / 2;
    const relY = centerY - TARGET_H / 2;

    const newOffsetX = relX - (relX - currentOffsetX) * zoomFactor;
    const newOffsetY = relY - (relY - currentOffsetY) * zoomFactor;

    zoomInput.value = String(nextZoom);
    offsetXInput.value = String(clamp(Math.round(newOffsetX), -maxOffsetX, maxOffsetX));
    offsetYInput.value = String(clamp(Math.round(newOffsetY), -maxOffsetY, maxOffsetY));
    render();
  };

  modeInput.addEventListener("change", () => {
    const zoomRatio = getZoomScale();
    baseScale = computeBaseScale();
    zoomInput.value = String(clamp(Math.round(zoomRatio * 100), 50, 300));
    render();
  });

  [zoomInput, offsetXInput, offsetYInput].forEach((control) => {
    control.addEventListener("input", render);
  });

  rotateLeftButton.addEventListener("click", () => {
    rotation = (rotation + 270) % 360;
    baseScale = computeBaseScale();
    render();
  });

  rotateRightButton.addEventListener("click", () => {
    rotation = (rotation + 90) % 360;
    baseScale = computeBaseScale();
    render();
  });

  flipXButton.addEventListener("click", () => {
    flipX *= -1;
    updateFlipButtons();
    render();
  });

  flipYButton.addEventListener("click", () => {
    flipY *= -1;
    updateFlipButtons();
    render();
  });

  resetButton.addEventListener("click", resetView);

  canvas.addEventListener(
    "wheel",
    (e) => {
      e.preventDefault();
      const rect = canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const delta = e.deltaY < 0 ? 6 : -6;
      zoomBy(delta, x, y);
    },
    { passive: false }
  );

  const getDistance = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);

  canvas.addEventListener("pointerdown", (e) => {
    canvas.setPointerCapture(e.pointerId);
    pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });

    if (pointers.size === 1) {
      panStart = {
        x: e.clientX,
        y: e.clientY,
        offsetX: getOffsetX(),
        offsetY: getOffsetY(),
      };
      pinchStart = null;
      return;
    }

    if (pointers.size === 2) {
      const [p1, p2] = [...pointers.values()];
      pinchStart = {
        distance: getDistance(p1, p2),
        zoom: Number(zoomInput.value),
      };
      panStart = null;
    }
  });

  canvas.addEventListener("pointermove", (e) => {
    if (!pointers.has(e.pointerId)) return;
    pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });

    if (pointers.size === 2 && pinchStart) {
      const [p1, p2] = [...pointers.values()];
      const distance = getDistance(p1, p2);
      if (!pinchStart.distance) return;

      const zoomRatio = distance / pinchStart.distance;
      const nextZoom = clamp(Math.round(pinchStart.zoom * zoomRatio), 50, 300);
      if (nextZoom !== Number(zoomInput.value)) {
        zoomInput.value = String(nextZoom);
        render();
      }
      return;
    }

    if (pointers.size === 1 && panStart) {
      const dx = e.clientX - panStart.x;
      const dy = e.clientY - panStart.y;
      offsetXInput.value = String(clamp(Math.round(panStart.offsetX + dx), -maxOffsetX, maxOffsetX));
      offsetYInput.value = String(clamp(Math.round(panStart.offsetY + dy), -maxOffsetY, maxOffsetY));
      render();
    }
  });

  const clearPointer = (e) => {
    pointers.delete(e.pointerId);
    if (pointers.size === 0) {
      panStart = null;
      pinchStart = null;
    } else if (pointers.size === 1) {
      const p = [...pointers.values()][0];
      panStart = {
        x: p.x,
        y: p.y,
        offsetX: getOffsetX(),
        offsetY: getOffsetY(),
      };
      pinchStart = null;
    }

    try {
      canvas.releasePointerCapture(e.pointerId);
    } catch (_err) {
      // Ignore capture release races.
    }
  };

  canvas.addEventListener("pointerup", clearPointer);
  canvas.addEventListener("pointercancel", clearPointer);
  canvas.addEventListener("pointerleave", clearPointer);

  saveButton.addEventListener("click", async () => {
    saveButton.disabled = true;
    saveButton.textContent = "Saving...";

    try {
      const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
      if (!blob) throw new Error("Failed to build processed image");

      const formData = new FormData();
      formData.append("processed_image", blob, "processed.png");
      formData.append("mode", modeInput.value === "cover" ? "manual_cover" : "manual_contain");

      const response = await fetch(`/crop/${imageId}/save`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Save failed (${response.status})`);
      }

      const payload = await response.json();
      window.location.href = payload.next_url || "/";
    } catch (err) {
      console.error(err);
      alert("Could not save this crop. Please retry.");
      saveButton.disabled = false;
      saveButton.textContent = "Save and Continue";
    }
  });

  image.onload = () => {
    baseScale = computeBaseScale();
    updateFlipButtons();
    render();
  };

  image.src = imageSrc;
})();
