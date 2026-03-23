function showOverlay(message) {
  const overlay = document.getElementById("overlay");
  const msg = document.getElementById("overlay-message");
  if (!overlay || !msg) return;
  msg.textContent = message || "Working...";
  overlay.classList.add("show");
}

function hideOverlay() {
  const overlay = document.getElementById("overlay");
  if (!overlay) return;
  overlay.classList.remove("show");
}

