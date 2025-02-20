import "./lucide-icon.js";

class AppDrawer extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({mode: "open"});
    this.isOpen = false;
    this.handleKeydown = this.handleKeydown.bind(this);
  }

  static get observedAttributes() {
    return ["position", "button-text"];
  }

  connectedCallback() {
    this.position = this.getAttribute("position") || "left";
    this.buttonText = this.getAttribute("button-text") || "menu";
    this.render();
    this.setupListeners();
    document.addEventListener("keydown", this.handleKeydown);
  }

  render() {
    const template = `
        <div class="drawer-container ${this.isOpen ? "open" : ""}">
          <button class="trigger-button" type="button">
            <lucide-icon variant="primary" name="${this.buttonText}"></lucide-icon>
          </button>

          <div class="backdrop"></div>

          <div class="drawer">
            <div class="drawer-content">
              <slot></slot>
            </div>
          </div>
        </div>

        <style>
          .drawer-container {
            pointer-events: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            z-index: 1000;
          }

          .drawer-container.open {
            pointer-events: all;
          }

          .trigger-button {
            position: fixed;
            top: 1rem;
            padding: 0.75rem;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 0.5rem;
            cursor: pointer;
            z-index: 1001;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s ease;
            pointer-events: all;
          }

          .trigger-button:hover {
            background: var(--surface-hover);
          }

          :host([position="left"]) .trigger-button {
            left: 1rem;
          }

          :host([position="right"]) .trigger-button {
            right: 1rem;
          }

          .backdrop {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.5);
            opacity: 0;
            transition: opacity 0.3s ease;
            visibility: hidden;
          }

          .drawer-container.open .backdrop {
            opacity: 1;
            visibility: visible;
          }

          .drawer {
            position: fixed;
            top: 0;
            bottom: 0;
            width: 300px;
            background: var(--surface);
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
            padding: 1rem;
            transition: transform 0.3s ease;
          }

          :host([position="left"]) .drawer {
            left: 0;
            transform: translateX(-100%);
          }

          :host([position="right"]) .drawer {
            right: 0;
            transform: translateX(100%);
          }

          .drawer-container.open .drawer {
            transform: translateX(0);
          }

          .drawer-content {
            overflow-y: auto;
            height: 100%;
          }
        </style>
      `;

    this.shadowRoot.innerHTML = template;
  }

  setupListeners() {
    const triggerButton = this.shadowRoot.querySelector(".trigger-button");
    const backdrop = this.shadowRoot.querySelector(".backdrop");

    triggerButton.addEventListener("click", () => this.toggle());
    backdrop.addEventListener("click", () => this.close());
  }

  handleKeydown(e) {
    if (e.key === "Escape" && this.isOpen) {
      this.close();
    }
  }

  toggle() {
    if (this.isOpen) {
      this.close();
    } else {
      this.open();
    }
  }

  open() {
    this.isOpen = true;
    this.shadowRoot.querySelector(".drawer-container").classList.add("open");
    document.body.style.overflow = "hidden";
  }

  close() {
    this.isOpen = false;
    this.shadowRoot.querySelector(".drawer-container").classList.remove("open");
    document.body.style.overflow = "";
  }

  disconnectedCallback() {
    document.removeEventListener("keydown", this.handleKeydown);
  }

  attributeChangedCallback(name, oldValue, newValue) {
    if (oldValue !== newValue && this.shadowRoot.innerHTML !== "") {
      this.render();
      this.setupListeners();
    }
  }
}

customElements.define("app-drawer", AppDrawer);
