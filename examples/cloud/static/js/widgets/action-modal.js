import { LitElement, html } from 'https://unpkg.com/@polymer/lit-element@0.7.1/lit-element.js?module';

class ActionModal extends LitElement {
  static get properties() {
    return {
      href: { type: String },
      title: { type: String },
      submitText: { type: String },
      form: { type: Object }
    }
  }

  constructor() {
    super();
    this.form = {};
  }

  firstUpdated() {
    fetch(this.href)
      .then((r) => r.json())
      .then((r) => {
        console.log(r)
        this.form = r.data.form;
      });
  }

  createRenderRoot() {
    return this;
  }

  render() {
    const { form, title } = this;
    const fields = form.fields || [];
    return html`
      <h3>${title}</h3>
      <form class="beta-hxForm" id="action-form-modal">
        <fieldset>
          ${fields.map(field => html`
            <label for=${field.name} class="hxSubdued">
              <abbr title="required">*</abbr>
              <span>${field.label}</span>
              <input class="hxTextCtrl" type=${field.widget.type} value=${field.data} name=${field.name} />
              ${field.description ? html`<p class="hxSubdued helpText">${field.description}</p>` : '' }
            </label>
          `)}
        </fieldset>
      </form>
      <footer>
        <button class="hxBtn hxPrimary">Submit</button>
        <button class="hxBtn">Cancel</button>
      </footer>
    `;
  }
}

customElements.define('action-modal', ActionModal);
