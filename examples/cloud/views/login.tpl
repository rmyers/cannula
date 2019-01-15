<!doctype html>
<html>
  <head>
    <title>Frankly</title>
    <link rel="stylesheet" href="https://unpkg.com/helix-ui@0.14.0/dist/styles/helix-ui.min.css"></link>
    <link rel="stylesheet" href="/static/css/main.css"></link>
  </head>
  <body>
    <div class='wrapper'>
      <h1 class="header">Login</h1>
      <nav>
        Login First
      </nav>
      <article>
        <h2>Please Login</h2>
        <p>Try one of these usernames</p>
        <ul>
          <li>admin (full site admin)</li>
          <li>create (create access)</li>
          <li>read (read only user)</li>
          <li>write (all access)</li>
          <li>managed (privileged customer)</li>
        </ul>
        <form action="." method="POST" id="login">
          <label for="username">Username: </label>
            <input class="hxTextCtrl" placeholder="username" type="text" name="username" />
          <label for="password">Password: </label>
            <input class="hxTextCtrl" placeholder="password" type="password" name="password" />
            <button type="submit" form="login" value="Login">Login</button>
        </form>
      </article>

      <footer>
        Copyright (c) 2019 Cannula Team
      </footer>
  </body>
</html>
