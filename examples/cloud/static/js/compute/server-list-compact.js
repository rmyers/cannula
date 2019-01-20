import {LitElement, html} from 'https://unpkg.com/@polymer/lit-element@0.6.3/lit-element.js?module';

import { Column } from '../tables/column.js';
import { flavorRam } from './helpers.js';
import '../tables/data_table.js';

const columns = [
  new Column('id'),
  new Column('name'),
  new Column(flavorRam, {header: 'flavor'}),
]

class ServerListCompact extends LitElement {
  static get properties() {
    return {
      servers: { type: Array },
      errors: { type: Array }
    }
  }

  constructor() {
    super();
    this.servers = [];
    this.errors = [];
  }

  render() {
    const { servers, errors } = this;
    return html`
      <h2>Servers</h2>
      <data-table .data=${servers} .columns=${columns} .errors=${errors}></data-table>
    `;
  }
}

customElements.define('server-list-compact', ServerListCompact);
