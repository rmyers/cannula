<!doctype html>
<html>
  <head>
    <title>Frankly</title>
    <link rel="stylesheet" href="https://unpkg.com/helix-ui@0.14.0/dist/styles/helix-ui.min.css"></link>
    <link rel="stylesheet" href="/static/css/main.css"></link>
  </head>
  <body class="hxHorizontal" id="top">
  <!-- Accessibility: This link should be the first item in tab order. -->
  <a href="#content">Skip to main content</a>

  <header id="head">
    <!-- TODO (user component) -->
  </header>

  <div id="app">
    <main role="main" id="content">
      <hx-panel class="hxSpan-3-xs login">
        <hx-panelbody>
          <h1>Please Login</h1>
          <p>Try one of these usernames:</p>
          <ul>
            <li>admin (full site admin)</li>
            <li>create (create access)</li>
            <li>read (read only user)</li>
            <li>write (all access)</li>
            <li>managed (privileged customer)</li>
          </ul>
          <form action="." method="POST" id="login" class="beta-hxForm">
            <fieldset>
              <label for="username">Username:</label>
              <input class="hxTextCtrl" placeholder="username" type="text" name="username" />
              <label for="password">Password:</label>
              <input class="hxTextCtrl" placeholder="password" type="password" name="password" />
            </fieldset>
              <button type="submit" form="login" value="Login">Login</button>
          </form>
        </hx-panelbody>
      </hx-panel>
    </main>
  </div>

  <footer id="foot">
    &copy; 2019 Cannula Team
    <nav>
      <a href="#terms">Website Terms</a>
      <a href="#privacy">Privacy Policy</a>
    </nav>
  </footer>
  <!-- UI toolkit JS -->
  <script src="https://unpkg.com/helix-ui@0.14.0/dist/scripts/helix-ui.browser.min.js"></script>
  </body>
</html>
