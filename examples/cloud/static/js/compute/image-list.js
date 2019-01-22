import {LitElement, html} from 'https://unpkg.com/@polymer/lit-element@0.7.1/lit-element.js?module';

import { Column } from '../tables/column.js';
import '../tables/data_table.js';

const columns = [
  new Column('name', {sortable: true, sorted: true}),
  new Column('minRam', { header: 'Min Ram', sortable: true, align: 'hxRight'}),
]

class ImageList extends LitElement {
  static get properties() {
    return {
      images: { type: Array },
      errors: { type: Array }
    }
  }

  constructor() {
    super();
    this.images = [];
    this.errors = [];
  }

  createRenderRoot() {
    return this;
  }

  render() {
    const { images, errors } = this;
    const className = 'hxTable--condensed';
    return html`
      <h2>Available Images</h2>
      <data-table .data=${images} .columns=${columns} .errors=${errors} .className=${className}></data-table>
    `;
  }
}

customElements.define('image-list', ImageList);
