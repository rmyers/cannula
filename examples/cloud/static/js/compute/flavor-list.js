import {LitElement, html} from 'https://unpkg.com/@polymer/lit-element@0.6.3/lit-element.js?module';

import { Column } from '../tables/column.js';
import '../tables/data_table.js';

const columns = [
  new Column('id'),
  new Column('name'),
  new Column('ram'),
]

class FlavorList extends LitElement {
  static get properties() {
    return {
      flavors: { type: Array }
    }
  }

  constructor() {
    super();
    this.flavors = [];
  }

  render() {
    const { flavors } = this;
    return html`
      <h2>Flavors</h2>
      <data-table .data=${flavors} .columns=${columns}></data-table>
    `;
  }
}

customElements.define('flavor-list', FlavorList);
