import {LitElement, html} from 'https://unpkg.com/@polymer/lit-element@0.7.1/lit-element.js?module';

class DashboardChart extends LitElement {
  static get properties() {
    return {
      chartType: { type: String },
      chartData: { type: Object }
    }
  }

  constructor() {
    super();
    this._chart = null;
    this.chartType = 'doughnut';
    this.chartData = {}
  }

  firstUpdated() {
    // Store a reference to the canvas element for easy access
    this._canvas = this.shadowRoot.querySelector('canvas').getContext('2d');
    const { chartData, chartType } = this;
    if (!this._chart) {
      this._chart = new Chart(this._canvas, {
        type: chartType,
        data: chartData
      });
    } else {
      this._chart.data = chartData;
      this._chart.type = chartType;
      this._chart.update();
    }
  }

  render() {
    return html`
      <style>
        .chart-size{
            position: relative;
            width:250px;
            height:150px;
        }
      </style>
      <div class="chart-size">
        <canvas></canvas>
      </div>
    `;
  }
}

customElements.define('dashboard-chart', DashboardChart);
