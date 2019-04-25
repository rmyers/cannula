/*
 * Delete window.fetch and fall back to xhr requests from fetch polyfill.
 * see: https://github.com/cypress-io/cypress/issues/95
 */
Cypress.on('window:before:load', (win) => {
  delete win.fetch
});

Cypress.on('uncaught:exception', () => {return false});

describe('Test Dashboard', function() {
  beforeEach(() => {
    cy.login()
    cy.addMocks({
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
    });
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
});
