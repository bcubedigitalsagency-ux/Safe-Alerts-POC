console.log('SafeAlerts POC JS Loaded');

// Show loader for 3s on each page load
window.addEventListener("load", () => {
  const overlay = document.getElementById("loading-overlay");
  setTimeout(() => {
    overlay.classList.add("hidden");
  }, 3000); // 3 seconds
});

// Show loader again on navigation clicks
document.addEventListener("DOMContentLoaded", () => {
  const overlay = document.getElementById("loading-overlay");
  document.querySelectorAll("a").forEach(link => {
    link.addEventListener("click", e => {
      if (link.target !== "_blank" && link.href) {
        overlay.classList.remove("hidden");
      }
    });
  });
});
