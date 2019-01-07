import { html } from 'https://unpkg.com/@polymer/lit-element@0.6.3/lit-element.js?module';

/**
 * Default cell template.
 * @param {string|number} data - Data to display.
 * @return {string}
 */
const defaultCell = (data) => html`<div class="data-table-cell">${data}</div>`;

/** Default options for the Column constructor. */
const defaultOptions = {
  attribute: undefined,
  defaultValue: '',
  header: undefined,
  className: undefined,
  cell: defaultCell
}

/**
 * Column of a data-table object. This handles the header for the column as
 * well a retrieving the display data for the table. When you create a new
 * data-table you can specify any number of columns. The data-table will take
 * an array of objects which each item is passed to the Column object to
 * get the cell data.
 *
 * The data-table is responsible for filtering or sorting the rows. The column
 * can return the data with the `getData()` function which can then be
 * used to sort or filter the data.
 */
export class Column {

  /**
   * Create a Column
   * @param {string} attribute - The attribute to display.
   * @param {defaultOptions} options - Optional settings.
   */
  constructor (attribute, options) {
    let opts = Object.assign({}, defaultOptions, options);
    this.attribute = attribute;
    this.defaultValue = opts.defaultValue;
    this.header = opts.header || attribute;
    this.className = opts.className || `${this.header}-column`;
    this.cell = opts.cell;
  }

  /**
   * Return the value of the attribute on the dataModel object.
   * @param {object} dataModel - A single item from the data table.
   * @return {string|number|Object}
   */
  getData(dataModel) {
    if (typeof this.attribute === "function") {
      return this.attribute(dataModel);
    }
    return dataModel[this.attribute] || this.defaultValue;
  }

  /**
   * Return the cell data.
   * For simple cases this just returns a the data wrapped in a div. You can
   * override the cell to provide a richer html response.
   * @param {object} dataModel - A single item from the data table.
   * @return {string}
   */
  getCell(dataModel) {
    const data = this.getData(dataModel);
    return this.cell(data);
  }
}
