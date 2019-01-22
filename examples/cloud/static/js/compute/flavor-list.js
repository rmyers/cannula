import {LitElement, html} from 'https://unpkg.com/@polymer/lit-element@0.7.1/lit-element.js?module';

import { Column } from '../tables/column.js';
import '../tables/data_table.js';

const columns = [
  new Column('name', {sortable: true, sorted: true}),
  new Column('ram', {sortable: true, align: 'hxRight'}),
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

  createRenderRoot() {
    return this;
  }

  render() {
    const { flavors, errors } = this;
    const className = 'hxTable--condensed';
    return html`
      <h2>Available Flavors</h2>
      <data-table .data=${flavors} .columns=${columns} .errors=${errors} .className=${className}></data-table>
    `;
  }
}

customElements.define('flavor-list', FlavorList);
