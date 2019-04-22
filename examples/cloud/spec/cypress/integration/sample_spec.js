/*
 * Delete window.fetch and fall back to xhr requests from fetch polyfill.
 * see: https://github.com/cypress-io/cypress/issues/95
 */
Cypress.on('window:before:load', (win) => {
  delete win.fetch
});

var mocks = JSON.stringify({
  "ComputeServer": {
    "__typename": "ComputeServer",
    "name": "frank",
    "id": "1233455"
  }
});

describe('Test Login Page', function() {
  it('Visits the login page', function() {
    cy.server({
      onAnyRequest: function(route, proxy) {
        proxy.xhr.setRequestHeader('X-Mock-Objects', mocks);
      }
    });
    cy.visit('http://localhost:8081/dashboard');
  })
});
