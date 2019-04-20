describe('Test Login Page', function() {
  it('Visits the login page', function() {
    cy.visit(
      'http://localhost:8081/dashboard', {
        headers: {
          'X-Mock-Objects': JSON.stringify({
            "ComputeServer": {
              "__typename": "ComputeServer",
              "name": "frank",
              "id": "1233455"
            }
          })
        }
      })
  })
})
