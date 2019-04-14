import {LitElement, html} from 'https://unpkg.com/@polymer/lit-element@0.7.1/lit-element.js?module';

import './app-navigation.js';
import './compute/flavor-list.js';
import './compute/image-list.js';
import './dashboard/chart.js';
import './dashboard/resource-list.js';

class SimpleApp extends LitElement {
  static get properties() {
    return {
      flavors: { type: Array },
      images: { type: Array },
      servers: { type: Array },
      nav: { type: Array },
      errors: { type: Object },
      loaded: { type: Boolean },
      pollingInterval: { type: Number }
    }
  }

  constructor() {
    super();
    this.servers = [];
    this.flavors = [];
    this.images = [];
    this.nav = [];
    this.errors = {};
    this.loaded = false;
    this.pollingInterval = 5000;
  }

  /*
   * Fetch data from the server at the specified polling interval
   */
  _fetchData() {
    // Only preform the fetch if the browser is in focus cause they aren't
    // looking at it anyway, if you want you can still do it
    if ( document.hasFocus() ) {
      fetch('?xhr=1')
        .then((response) => response.json())
        .then((response) => {
          this.loaded = true;
          this.data = response.data;
          this.errors = response.errors;
          console.log('Polling for updates.');
        });
    }
  }

  firstUpdated() {
    const { pollingInterval } = this;
    if (pollingInterval) {
      // Setup the request to poll you need to bind the function this
      // in order for the response to update our properties.
      setInterval(this._fetchData.bind(this), pollingInterval);
    }
    this._fetchData()
  }

  createRenderRoot() {
    return this;
  }

  render() {
    const { data, errors, loaded } = this;
    let errorMessages = null;
    if (!loaded) {
      return html`
        <div id="stage" class="wrapper">
          <app-navigation></app-navigation>
          <main role="main" id="content">
            <hx-panel>
              <h1>Resources</h1>
              <hx-busy></hx-busy>
            </hx-panel>
          </main>
        </div>
      `;
    }

    if (errors && errors.errors) {
      errorMessages = errors.errors.map((error) => html`<hx-toast type="error">${error}</hx-toast>`)
    }

    return html`
    <div id="stage" class="wrapper">
      <app-navigation .navItems=${data.nav} .errors=${errors.nav}></app-navigation>
      <main role="main" id="content">
        <hx-panel class="hxSpan-8-xs">
          <hx-div scroll="both">
            <hx-panelbody class="hxBox hxMd">
              <h1>Server List</h1>
              <resource-list .resources=${data.resources} .errors=${errors.resources}></resource-list>
            </hx-panelbody>
          </hx-div>
        </hx-panel>
        <hx-panel class="hxSpan-4-xs">
          <hx-div scroll="both">
            <hx-panelbody class="hxBox hxMd">
              ${errorMessages}
              <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor
              incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud
              exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute
              irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla
              pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia
              deserunt mollit anim id est laborum.</p>
            </hx-panelbody>
          </hx-div>
        </hx-panel>
      </main>
    </div>
    <hx-modal id="app-action-modal"></hx-modal>
    `;
  }
}

customElements.define('simple-app', SimpleApp);
