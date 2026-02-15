(() => {
  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("files");

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
      fileInput.files = e.dataTransfer.files;
    });
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
