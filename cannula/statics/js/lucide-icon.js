/**
 * Available icons these are copied from Lucide https://lucide.dev/icons/
 *
 * To add a new one just pick a name copy the contents of the svg here. Only include the
 * contents of the svg and remove the <svg *></svg> tags as that is added by the component.
 */
const icons = {
  menu: '<line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line>',
  home: '<path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path><polyline points="9 22 9 12 15 12 15 22"></polyline>',
  settings:
    '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>',
  moon: '<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/>',
};

class LucideIcon extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({mode: "open"});
  }

  static get observedAttributes() {
    return ["name", "size", "variant"];
  }

  connectedCallback() {
    this.render();
  }

  attributeChangedCallback() {
    this.render();
  }

  render() {
    const name = this.getAttribute("name");
    const iconPath = icons[name] || "";

    this.shadowRoot.innerHTML = `
        <svg
          xmlns="http://www.w3.org/2000/svg"
          class="icon"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >${iconPath}</svg>

        <style>
          :host {
            display: inline-flex;
            width: 24px;
            height: 24px;
          }

          :host([size="small"]) {
            width: 16px;
            height: 16px;
          }

          :host([size="large"]) {
            width: 32px;
            height: 32px;
          }

          .icon {
            width: 100%;
            height: 100%;
            color: var(currentColor);
            transition: all 0.2s ease;
          }

          :host([variant="primary"]) .icon {
            color: var(--primary);
          }

          :host([variant="muted"]) .icon {
            color: var(--text-secondary);
          }
        </style>
      `;
  }
}

customElements.define("lucide-icon", LucideIcon);
