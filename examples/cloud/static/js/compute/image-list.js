import {LitElement, html} from 'https://unpkg.com/@polymer/lit-element@0.6.3/lit-element.js?module';

import { Column } from '../tables/column.js';
import '../tables/data_table.js';

const columns = [
  new Column('id'),
  new Column('name'),
  new Column('minRam', { header: 'Min Ram'}),
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

  render() {
    const { images, errors } = this;
    return html`
      <h2>Images</h2>
      <data-table .data=${images} .columns=${columns} .errors=${errors}></data-table>
    `;
  }
}

customElements.define('image-list', ImageList);
