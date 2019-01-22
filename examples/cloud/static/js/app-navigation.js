import {LitElement, html} from 'https://unpkg.com/@polymer/lit-element@0.7.1/lit-element.js?module';

const renderItem = (item) => {
  if (item.enabled) {
    return html`<a href="${item.url}">${item.name}</a>`;
  }
  return html`<a href="#" title="${item.disabledMessage}" disabled>${item.name}</a>`;
}

const renderSection = (section) => {
  return html`
    <hx-disclosure aria-controls="${section.title}">
      ${section.title}
    </hx-disclosure>
    <hx-reveal id="${section.title}" open>
      ${section.items.map(renderItem)}
    </hx-reveal>
  `;
}

class AppNavigation extends LitElement {
  static get properties() {
    return {
      navItems: { type: Array },
    }
  }

  constructor() {
    super();
    this.navItems = [];
  }

  createRenderRoot() {
    return this;
  }

  render() {
    const { navItems } = this;
    return html`
      <nav id="nav" class="hxNav main-navigation">
        ${navItems.map(renderSection)}
      </nav>
    `;
  }
}

customElements.define('app-navigation', AppNavigation);
