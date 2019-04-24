// ***********************************************
// This example commands.js shows you how to
// create various custom commands and overwrite
// existing commands.
//
// For more comprehensive examples of custom
// commands please read more here:
// https://on.cypress.io/custom-commands
// ***********************************************
//
// Custom Login Command
Cypress.Commands.add("login", (username, password) => {
  cy.visit('http://localhost:8081/')
  cy.get('input[name="username"]').type(username || 'admin')
  cy.get('input[name="password"]').type(password || 'password')
  cy.get('button[type=submit]').click()
});
