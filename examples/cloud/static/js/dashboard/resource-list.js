import {LitElement, html} from 'https://unpkg.com/@polymer/lit-element@0.7.1/lit-element.js?module';

import { Column } from '../tables/column.js';
import '../tables/data_table.js';
import { statusCell } from '../widgets/status-cell.js';
import { actionCell } from '../widgets/action-cell.js';


const columns = [
  new Column('appActions', {cell: actionCell, header: html`<hx-icon type="cog"></hx-icon>`, defaultValue: []}),
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
    const className = "hxHoverable resource-list";
    return html`
      <data-table .data=${resources} .columns=${columns} .errors=${errors} .className=${className}></data-table>
    `;
  }
}

customElements.define('resource-list', ResourceList);
