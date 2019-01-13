import {LitElement, html} from 'https://unpkg.com/@polymer/lit-element@0.6.3/lit-element.js?module';

import './compute/server-list-compact.js';
import './compute/flavor-list.js';
import './compute/image-list.js';
import './app-navigation.js';

class OpenstackApp extends LitElement {
  static get properties() {
    return {
      flavors: { type: Array },
      images: { type: Array },
      servers: { type: Array },
      nav: { type: Array },
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
          this.nav = response.nav;
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

  createRenderRoot() {
    return this;
  }

  render() {
    const { servers, flavors, images, nav, loaded } = this;
    if (!loaded) {
      return html`<p>Loading...</p>`
    }
    return html`
    <div class="wrapper">
    <h1 class="header">Dashboard</h1>
    <app-navigation .navItems=${nav}></app-navigation>
    <article>
      <flavor-list .flavors=${flavors}></flavor-list>
      <image-list .images=${images}></image-list>
      <server-list-compact .servers=${servers}></server-list-compact>
    </article>
    <aside>
      This is an aside…
    </aside>

    <footer>
      Copyright (c) 2019 Cannula Team
    </footer>
    </div>
    `;
  }
}

customElements.define('openstack-app', OpenstackApp);
