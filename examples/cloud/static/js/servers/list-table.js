import {LitElement, html} from 'https://unpkg.com/@polymer/lit-element@0.6.3/lit-element.js?module';


class ServerListTable extends LitElement {
  static get properties() {
    return {
      servers: { type: Array }
    }
  }

  constructor() {
    super();
    this.servers = [];
  }

  _serverList() {
    const { servers } = this;
    if (servers.length === 0){
      return html`<table class="server-list">No servers yet</table>`
    }
  }

  render() {
    const { servers } = this;
    if (servers.length === 0){
      return html`<div class="server-list">No servers yet</div>`
    }
    return html`
      <div class="server-list">
        <ul>
          ${servers.map((item) => {
            return html`<li>${item.name}</li>`;
          })
        }
        </ul>
      </div>
      `;
  }
}

customElements.define('server-list-table', ServerListTable);
