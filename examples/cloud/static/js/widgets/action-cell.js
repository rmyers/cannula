import { html } from 'https://unpkg.com/@polymer/lit-element@0.7.1/lit-element.js?module';
import { render } from 'https://unpkg.com/lit-html?module';

import './action-modal.js';

const actionModal = (formUrl, title) => {
  return html`<action-modal href=${formUrl} title=${title}></action-modal>`
}

const openModal = (formUrl, title, menuId) => {
  const modalElement = document.getElementById('app-action-modal');
  const parentMenu = document.getElementById(menuId);
  render(actionModal(formUrl, title), modalElement);
  modalElement.open = true;
  parentMenu.open = false;
}

const actionPopover = (action, menuId) => {
  if (action.enabled) {
    return html`
      <hx-menuitem>
        <a href="#" @click=${() => openModal(action.formUrl, action.label, menuId)}>${action.label}</a>
      </hx-menuitem>
    `;
  }
  return html`
    <hx-menuitem>
      <a href="#" title=${action.tooltip} disabled>${action.label}</a>
    </hx-menuitem>
  `;
}


export const actionCell = (actions, id) => {
  const actionList = actions || [];
  const menuId = `action-menu-${id}`;
  return html`
    <hx-disclosure aria-controls="${menuId}">
      <hx-icon type="cog"></hx-icon>
    </hx-disclosure>
    <hx-menu id="${menuId}">
      ${actionList.map((item) => actionPopover(item, menuId))}
    </hx-menu>
  `
};
