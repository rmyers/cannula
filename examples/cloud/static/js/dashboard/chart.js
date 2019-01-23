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
    this.chartData = {};
  }

  firstUpdated() {
    const { chartData, chartType } = this;
    let _canvas = this.shadowRoot.querySelector('canvas').getContext('2d');
    if (!this._chart) {
      this._chart = new Chart(_canvas, {
        type: chartType,
        data: chartData
      });
    } else {
      this._chart.data = chartData;
      this._chart.type = chartType;
      this._chart.update();
    }
  }

  updated(changedProperties) {
    const { chartData, _chart } = this;
    changedProperties.forEach((oldValue, propName) => {
      if (propName === 'chartData' && oldValue) {
        // Test if we need to update the chart with new values since we
        // are not directly using an lit-html template for these values.
        // Probably is a better way... but this works good enough!
        let origData = oldValue.datasets[0].data.toString();
        let newData = chartData.datasets[0].data.toString();
        if (origData !== newData) {
          _chart.data = chartData;
          _chart.update();
        }
      }
    });
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
