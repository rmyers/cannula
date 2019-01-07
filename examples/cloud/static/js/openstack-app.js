import {LitElement, html} from 'https://unpkg.com/@polymer/lit-element@0.6.3/lit-element.js?module';

import { AppStyles } from './style.js';
import './compute/server-list-compact.js';
import './compute/flavor-list.js';
import './compute/image-list.js';


class OpenstackApp extends LitElement {
  static get properties() {
    return {
      flavors: { type: Array },
      images: { type: Array },
      servers: { type: Array },
      loaded: { type: Boolean },
      pollingInterval: { type: Number }
    }
  }

  constructor() {
    super();
    this.servers = [];
    this.flavors = [];
    this.images = [];
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
          this.servers = response.servers;
          this.images = response.images;
          this.flavors = response.flavors;
          console.log('here');
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

  render() {
    const { servers, flavors, images, loaded } = this;
    if (!loaded) {
      return html`<p>Loading...</p>`
    }
    return html`
      ${AppStyles}
      <div class="main">
        <div class="row">
          <div class="sidebar">
            <p>boo</p>
          </div>
          <div class="content">
            <flavor-list .flavors=${flavors}></flavor-list>
            <image-list .images=${images}></image-list>
            <server-list-compact .servers=${servers}></server-list-compact>
          </div>
        </div>
      </div>
      `;
  }
}

customElements.define('openstack-app', OpenstackApp);
