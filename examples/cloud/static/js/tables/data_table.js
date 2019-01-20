import {LitElement, html} from 'https://unpkg.com/@polymer/lit-element@0.6.3/lit-element.js?module';

const defaultEmptyOverlay = html`<div class="data-table-empty">No results</div>`;
const defaultErrorOverlay = (errors) => {
  return html`
    <div class="data-table-error">
      ${errors.map((error) => html`<p>${error.message}</p>`)}
    </div>
  `;
}

export class DataTable extends LitElement {

  constructor () {
    super();
    this.columns = [];
    this.data = [];
    this.errors = [];
    this.displayData = [];
    this.emptyOverlay = defaultEmptyOverlay;
    this.errorOverlay = defaultErrorOverlay;
    this.className = 'data-table';
  }

  static get properties() {
    return {
      data: { type: Array },
      columns: { type: Array },
      errors: { type: Array },
      emptyOverlay: { type: String }
    };
  }

  _getHeader() {
    const { columns } = this;
    return html`
      <tr>
          ${columns.map((column) => html`<th>${column.header}</th>`)}
      </tr>
    `;
  }

  _showEmpty() {
    const { emptyOverlay } = this;
    const numberOfColumns = this.columns.length;
    return html`
      <tr>
        <td colspan="${numberOfColumns}">${emptyOverlay}</td>
      </tr>
    `;
  }

  _showError() {
    const { errorOverlay, errors } = this;
    const numberOfColumns = this.columns.length;
    return html`
      <tr>
        <td colspan="${numberOfColumns}">${errorOverlay(errors)}</td>
      </tr>
    `;
  }

  _getBody() {
    const { data, columns, errors } = this;
    if (errors && errors.length !== 0) {
      return this._showError();
    }

    if (!data || data.length === 0) {
      return this._showEmpty();
    }
    return html`
      ${data.map((item) => {
        return html`
          <tr>
            ${columns.map((column) => {return html`<td>${column.getCell(item)}</td>`})}
          </tr>
        `;
      })}
    `;
  }

  render() {
    return html`
      <table class="${this.className}">
        <thead>${this._getHeader()}</thead>
        <tbody>${this._getBody()}</tbody>
      </table>
    `;
  }
}

customElements.define('data-table', DataTable);
