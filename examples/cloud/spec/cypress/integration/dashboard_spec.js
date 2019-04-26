/*
 * Delete window.fetch and fall back to xhr requests from fetch polyfill.
 * see: https://github.com/cypress-io/cypress/issues/95
 */
Cypress.on('window:before:load', (win) => {
  delete win.fetch
});

Cypress.on('uncaught:exception', () => {return false});

const dashboardMocks = {
  'Query': {
    'resources': [
      {
        "__typename": "ComputeServer",
        "name": "server-first",
        "id": "1111111",
        "status": "active",
        "region": "us-east"
      },
      {
        "__typename": "Network",
        "name": "local-network",
        "id": "2222222",
        "status": "active",
        "region": "us-east"
      },
      {
        "__typename": "Volume",
        "name": "my-volume",
        "id": "3333333",
        "status": "active",
        "region": "us-east"
      }
    ]
  }
}

describe('Test Dashboard', function() {
  beforeEach(() => {
    cy.login()
    cy.addMocks(dashboardMocks);
  });

  it('Has a resource list title', function() {
    cy.visit('http://localhost:8081/dashboard')
    cy.get('h1').contains('Resources')
  });

  it('Has all the resources in the table', function () {
    cy.visit('http://localhost:8081/dashboard')
    cy.get('table.resource-list')
    .contains('server-first')
    cy.get('table.resource-list')
    .contains('my-volume')
    cy.get('table.resource-list')
    .contains('local-network')
  });

  it('Has the correct action menu items', function () {
    const formMocks = {
      'WTFBaseField': {
        'data': 'mock-network-name'
      }
    }
    cy.addMocks({...dashboardMocks, ...formMocks})
    cy.visit('http://localhost:8081/dashboard')
    cy.get('[aria-controls=action-menu-2222222]')
      .click()
    cy.get('#action-menu-2222222').find('hx-menuitem')
      .contains('Rename Network')
      .click()
    cy.get('#app-action-modal').within((el) => {
      cy.get('h3').contains('Rename Network')
      cy.get('label').contains('New Name')
      cy.get('input').should('have.value', 'mock-network-name')
      cy.get('.helpText').contains('Enter a new name for the network.')
    })
  });
});
