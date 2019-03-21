import { html } from 'https://unpkg.com/@polymer/lit-element@0.7.1/lit-element.js?module';

const actionPopover = (action, id) => {
  console.log(id);
  return html`
  <hx-menuitem>
  <hx-disclosure aria-controls="${action.label}-popover-${id}">
  ${action.label}
  </hx-disclosure>
  </hx-menuitem>
  <hx-modal id="${action.label}-popover-${id}">

      <h3>
      ${action.label}
      </h3>

      <footer>
        <button class="hxBtn hxPrimary">Submit</button>
        <button class="hxBtn">Cancel</button>
      </footer>
    </hx-modal>
    `
}


export const actionCell = (actions, id) => {
  const actionList = actions || [];
  return html`
    <hx-disclosure aria-controls="action-menu-${id}">
      <hx-icon type="cog"></hx-icon>
    </hx-disclosure>
    <hx-menu id="action-menu-${id}">
      ${actionList.map(actionPopover)}
    </hx-menu>
  `
};
