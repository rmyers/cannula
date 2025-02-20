import "/static/js/lucide-icon.js";

class ThemeToggle extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({mode: "open"});
    this.initializeTheme();
  }

  initializeTheme() {
    // Check localStorage first
    const savedTheme = localStorage.getItem("theme");

    if (savedTheme) {
      document.documentElement.setAttribute("data-theme", savedTheme);
    } else {
      // If no saved preference, check system preference
      const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
      document.documentElement.setAttribute("data-theme", prefersDark ? "dark" : "light");
      localStorage.setItem("theme", prefersDark ? "dark" : "light");
    }

    // Listen for system theme changes
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", (e) => {
      if (!localStorage.getItem("theme")) {
        const newTheme = e.matches ? "dark" : "light";
        document.documentElement.setAttribute("data-theme", newTheme);
      }
    });
  }

  setupListeners() {
    const toggle = this.shadowRoot.querySelector(".toggle");
    toggle.addEventListener("click", () => {
      const isDark = document.documentElement.getAttribute("data-theme") === "dark";
      document.documentElement.setAttribute("data-theme", isDark ? "light" : "dark");

      // Optionally save preference
      localStorage.setItem("theme", isDark ? "light" : "dark");
    });
  }

  connectedCallback() {
    this.render();
    this.setupListeners();
  }

  render() {
    this.shadowRoot.innerHTML = `
        <button class="toggle">
            <lucide-icon name="sun" variant="primary" class="light"></lucide-icon>
            <lucide-icon name="moon" variant="primary" class="dark"></lucide-icon>
        </button>

        <style>
            .toggle {
                background: var(--surface);
                border: 1px solid var(--border);
                padding: 0.5rem 1rem;
                border-radius: 0.5rem;
                cursor: pointer;
                font-size: 1.2rem;
                display: flex;
                align-items: center;
                justify-content: center;
            }

            .dark {
                display: none;
            }

            :host-context([data-theme="dark"]) .light {
                display: none;
            }

            :host-context([data-theme="dark"]) .dark {
                display: inline;
            }
        </style>
    `;
  }
}

// Register the component
customElements.define("theme-toggle", ThemeToggle);
