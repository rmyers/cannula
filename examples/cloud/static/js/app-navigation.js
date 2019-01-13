import {LitElement, html} from 'https://unpkg.com/@polymer/lit-element@0.6.3/lit-element.js?module';

const renderItem = (item) => {
  if (item.enabled) {
    return html`<li><a href="${item.url}">${item.name}</a></li>`;
  }
  return html`<li title="${item.disabledMessage}">${item.name}</li>`;
}

const renderSection = (section) => {
  return html`
    <h2>${section.title}</h2>
    <ul>
      ${section.items.map(renderItem)}
    </ul>
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

  _renderSections() {
    const { navItems } = this;

  }

  render() {
    const { navItems } = this;
    return html`
      <nav id="nav">
        ${navItems.map(renderSection)}
      </nav>
    `;
  }
}

customElements.define('app-navigation', AppNavigation);
