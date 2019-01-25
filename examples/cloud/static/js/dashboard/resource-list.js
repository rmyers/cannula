import {LitElement, html} from 'https://unpkg.com/@polymer/lit-element@0.7.1/lit-element.js?module';

import { Column } from '../tables/column.js';
import '../tables/data_table.js';

const statusCell = (status) => html`<hx-status class="${status.color}">${status.label}</hx-status>`;

const columns = [
  new Column('appStatus', {cell: statusCell, header: 'Status'}),
  new Column('name', {sortable: true, sorted: true}),
  new Column('id')
]

class ResourceList extends LitElement {
  static get properties() {
    return {
      resources: { type: Array },
      errors: { type: Array }
    }
  }

  constructor() {
    super();
    this.resources = [];
    this.errors = [];
  }

  createRenderRoot() {
    return this;
  }

  render() {
    const { resources, errors } = this;
    return html`
      <data-table .data=${resources} .columns=${columns} .errors=${errors}></data-table>
    `;
  }
}

customElements.define('resource-list', ResourceList);
