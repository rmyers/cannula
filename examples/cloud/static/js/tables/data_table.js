import {LitElement, html} from 'https://unpkg.com/@polymer/lit-element@0.7.1/lit-element.js?module';

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
      ${errors.map((error) => html`<p>${error}</p>`)}
    </div>
  `;
};

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
    const { sortable, sortDirection, header, sorted, align } = column;
    let columnIndex = index;
    if (!sortable) {
      return html`<th>${column.header}</th>`;
    }
    const sortedIcon = sortDirection === 'DESC' ? 'sort-down' : 'sort-up';
    const icon = sorted ? sortedIcon : 'sort';
    return html`<th class="sortable ${align}" @click=${() => sortIndexCallback(columnIndex)}>${header} <hx-icon class="toggle-icon" type="${icon}"></hx-icon></th>`;
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
    this.className = 'hxHoverable';
    this.sortIndex = -1;
  }

  static get properties() {
    return {
      data: { type: Array },
      columns: { type: Array },
      errors: { type: Array },
      emptyOverlay: { type: String },
      errorOverlay: { type: String },
      className: { type: String }
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
            ${columns.map((column) => {return html`<td class="${column.align}">${column.getCell(item)}</td>`})}
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

  createRenderRoot() {
    return this;
  }

  render() {
    return html`
      <table class="hxTable ${this.className}">
        <thead>${this._getHeader()}</thead>
        <tbody>${this._getBody()}</tbody>
      </table>
    `;
  }
}

customElements.define('data-table', DataTable);
