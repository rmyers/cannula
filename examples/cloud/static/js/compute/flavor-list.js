import {LitElement, html} from 'https://unpkg.com/@polymer/lit-element@0.6.3/lit-element.js?module';

import { Column } from '../tables/column.js';
import '../tables/data_table.js';

const columns = [
  new Column('id'),
  new Column('name', {sortable: true, sorted: true}),
  new Column('ram', {sortable: true, align: 'right'}),
]

class FlavorList extends LitElement {
  static get properties() {
    return {
      flavors: { type: Array },
      errors: { type: Array }
    }
  }

  constructor() {
    super();
    this.flavors = [];
    this.errors = [];
  }

  render() {
    const { flavors, errors } = this;
    return html`
      <h2>Flavors</h2>
      <data-table .data=${flavors} .columns=${columns} .errors=${errors}></data-table>
    `;
  }
}

customElements.define('flavor-list', FlavorList);
