/**
 * PlaylistPilot Notification Toast System
 */
const Notifications = {
  container: null,

  init() {
    if (!this.container) {
      let el = document.getElementById("toast-container");
      if (!el) {
        el = document.createElement("div");
        el.id = "toast-container";
        document.body.appendChild(el);
      }
      this.container = el;
    }
  },

  show(message, type = "info", duration = 4000) {
    this.init();
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    
    // Set text safely
    const textSpan = document.createElement("span");
    textSpan.textContent = message;
    toast.appendChild(textSpan);

    const closeBtn = document.createElement("button");
    closeBtn.className = "toast-close";
    closeBtn.innerHTML = "&times;";
    closeBtn.setAttribute("aria-label", "Close notification");
    closeBtn.onclick = () => toast.remove();
    toast.appendChild(closeBtn);

    this.container.appendChild(toast);

    if (duration > 0) {
      setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateX(100%)";
        toast.style.transition = "all 0.3s ease";
        setTimeout(() => toast.remove(), 300);
      }, duration);
    }
  },

  success(msg) {
    this.show(msg, "success");
  },

  error(msg) {
    this.show(msg, "error", 6000);
  },

  info(msg) {
    this.show(msg, "info");
  }
};

window.Notifications = Notifications;
