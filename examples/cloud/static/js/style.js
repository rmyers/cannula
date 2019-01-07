import { html } from 'https://unpkg.com/@polymer/lit-element@0.6.3/lit-element.js?module';

export const AppStyles = html`
<style>
  *,
  *::before,
  *::after {
    box-sizing: border-box;
  }

  body {
    margin: 0;
    padding: 0;
  }

  .main {
    width: 100%;
    min-height: 100%;
    margin: 0;
  }

  /* Prevent parent float collapsed problem */
  .row:after {
    display: table;
    clear: both;
    content: '';
  }

  @media (min-width: 700px) {
    .row .content {
      width: 60%;
      float: left;
    }
  }

  @media (min-width: 700px) {
    .row .sidebar {
      width: 30%;
      float: left;
      display: block;
    }
  }
</style>
`;
