import { html } from 'https://unpkg.com/@polymer/lit-element@0.7.1/lit-element.js?module';


export const statusCell = (status) => html`<hx-status class="${status.color}">${status.label}</hx-status>`;
