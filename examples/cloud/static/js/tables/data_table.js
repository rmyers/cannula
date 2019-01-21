import {LitElement, html, svg} from 'https://unpkg.com/@polymer/lit-element@0.6.3/lit-element.js?module';

/**
 * Default Empty Overlay
 * Used to display help content when there is no data.
 * @return {string}
 */
const defaultEmptyOverlay = html`<div class="data-table-empty">No results</div>`;

/**
 * Default Error Overlay
 * Used to display any errors that are passed in via the errors prop.
 * @param {Array} errors - List of errors to display
 * @return {string|html}
 */
const defaultErrorOverlay = (errors) => {
  return html`
    <div class="data-table-error">
      ${errors.map((error) => html`<p>${error.message}</p>`)}
    </div>
  `;
};

/**
 * Angle Down svg
 * Copied from fontawesome library https://fontawesome.com/license
 */
const angleDown = svg`<svg aria-hidden="true" data-prefix="fas" data-icon="angle-down" class="svg-inline--fa fa-angle-down fa-w-10" role="img" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 512"><path fill="currentColor" d="M143 352.3L7 216.3c-9.4-9.4-9.4-24.6 0-33.9l22.6-22.6c9.4-9.4 24.6-9.4 33.9 0l96.4 96.4 96.4-96.4c9.4-9.4 24.6-9.4 33.9 0l22.6 22.6c9.4 9.4 9.4 24.6 0 33.9l-136 136c-9.2 9.4-24.4 9.4-33.8 0z"></path></svg>`;

/**
 * Angle Up
 * Copied from fontawesome library https://fontawesome.com/license
 */
const angleUp = svg`<svg aria-hidden="true" data-prefix="fas" data-icon="angle-up" class="svg-inline--fa fa-angle-up fa-w-10" role="img" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 512"><path fill="currentColor" d="M177 159.7l136 136c9.4 9.4 9.4 24.6 0 33.9l-22.6 22.6c-9.4 9.4-24.6 9.4-33.9 0L160 255.9l-96.4 96.4c-9.4 9.4-24.6 9.4-33.9 0L7 329.7c-9.4-9.4-9.4-24.6 0-33.9l136-136c9.4-9.5 24.6-9.5 34-.1z"></path></svg>`;

/**
 * Default Sort Closure
 * @param {Column} column - The column to sort
 */
const defaultSort = (column) => {

  /**
   * Default sort function.
   * @param {any} first - First item to compare
   * @param {any} second - Second item to compare
   * @return {number}
   */
  return (first, second) => {
    const firstItem = column.getData(first);
    const secondItem = column.getData(second);
    const compared = firstItem.toString().localeCompare(secondItem);
    return column.sortDirection === 'DESC' ? compared : -compared;
  };
};

/**
 * Column Header Display
 * If the column is sortable this will include controls and a callback to
 * update the sortIndex and or the direction on the column.
 * @param {function} sortIndexCallback - Function to update the sort index.
 * @return {function}
 *
 */
const displayHeader = (sortIndexCallback) => {

  /**
   * Column Header Display
   * If the column is sortable this will include controls and a callback to
   * update the sortIndex and or the direction on the column.
   *
   * @param {Column} column - The column to display the header and controls for.
   * @param {number} index - The index of the column.
   * @return {string|html}
   */
  return (column, index) => {
    const { sortable, sortDirection, header, sorted } = column;
    let columnIndex = index;
    if (!sortable) {
      return html`<th>${column.header}</th>`;
    }
    const icon = sortDirection === 'DESC' ? angleDown : angleUp;
    const sortedClass = sorted ? 'sortable sorted' : 'sortable';
    return html`<th class=${sortedClass} @click=${() => sortIndexCallback(columnIndex)}>${header} ${icon}</th>`;
  };
};

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
    this.sortIndex = -1;
  }

  static get properties() {
    return {
      data: { type: Array },
      columns: { type: Array },
      errors: { type: Array },
      emptyOverlay: { type: String },
      errorOverlay: { type: String }
    };
  }

  _getHeader() {
    const { columns, _updateSortIndex } = this;
    const headerDisplay = displayHeader(_updateSortIndex.bind(this));
    return html`
      <tr>
          ${columns.map(headerDisplay)}
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

  _getFilteredData(data) {
    // TODO: make this work
    return data;
  }

  _getSortedData(data) {
    const { sortIndex, columns } = this;
    if (sortIndex >= 0) {
      let column = columns[sortIndex];
      return data.sort(defaultSort(column));
    }

    return data;
  }

  _filterAndSort(data) {
    let filtered = this._getFilteredData(data);
    let sorted = this._getSortedData(filtered);
    return sorted;
  }

  _updateSortIndex(index) {
    const { sortIndex, columns } = this;
    if (sortIndex === index) {
      columns[index].toggleSortDirection();
    } else {
      columns[this.sortIndex].sorted = false;
      columns[index].sorted = true;
      this.sortIndex = index;
    }
    this.update();
  }

  _getBody() {
    const { data, columns, errors } = this;
    if (errors && errors.length !== 0) {
      return this._showError();
    }

    if (!data || data.length === 0) {
      return this._showEmpty();
    }

    let sortedData = this._filterAndSort(data);

    return html`
      ${sortedData.map((item) => {
        return html`
          <tr>
            ${columns.map((column) => {return html`<td align="${column.align}">${column.getCell(item)}</td>`})}
          </tr>
        `;
      })}
    `;
  }

  connectedCallback() {
    super.connectedCallback();
    const { columns } = this;
    columns.map((column, index) => {
      if (column.sorted) {
        this.sortIndex = index;
      }
    });
  }

  render() {
    return html`
      <style>
        svg {height: 1em;}
        th.sortable {cursor: pointer;}
        th.sortable svg {color: #999;}
        th.sorted svg {color: #444;}
        th {text-transform: uppercase;}
        table {width: 100%}
        tr:hover {background-color: #f5f5f5;}
      </style>
      <table class="${this.className}">
        <thead>${this._getHeader()}</thead>
        <tbody>${this._getBody()}</tbody>
      </table>
    `;
  }
}

customElements.define('data-table', DataTable);
