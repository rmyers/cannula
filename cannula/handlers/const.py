GRAPHIQL_TEMPLATE = """
<!doctype html>
<html lang="en">
  <head>
    <title>GraphiQL</title>
    <style>
      body {
        height: 100%;
        margin: 0;
        width: 100%;
        overflow: hidden;
      }

      #graphiql {
        height: 100vh;
      }
    </style>
    <!--
      This GraphiQL example depends on Promise and fetch, which are available in
      modern browsers, but can be "polyfilled" for older browsers.
      GraphiQL itself depends on React DOM.
      If you do not want to rely on a CDN, you can host these files locally or
      include them directly in your favored resource bundler.
    -->
    <script
      crossorigin
      src="https://unpkg.com/react@18/umd/react.production.min.js"
    ></script>
    <script
      crossorigin
      src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"
    ></script>
    <!--
      These two files can be found in the npm module, however you may wish to
      copy them directly into your environment, or perhaps include them in your
      favored resource bundler.
     -->
    <script
      src="https://unpkg.com/graphiql/graphiql.min.js"
      type="application/javascript"
    ></script>
    <link rel="stylesheet" href="https://unpkg.com/graphiql/graphiql.min.css" />
    <!--
      These are imports for the GraphIQL Explorer plugin.
     -->
    <script
      src="https://unpkg.com/@graphiql/plugin-explorer/dist/index.umd.js"
      crossorigin
    ></script>

    <link
      rel="stylesheet"
      href="https://unpkg.com/@graphiql/plugin-explorer/dist/style.css"
    />
  </head>

  <body>
    <div id="graphiql">Loading...</div>
    <script>
      const root = ReactDOM.createRoot(document.getElementById('graphiql'));
      const fetcher = GraphiQL.createFetcher({
        url: window.location.href,
        subscriptionUrl: 'ws://' + window.location.host + window.location.pathname,
        headers: { 'X-Example-Header': 'foo' },
      });
      const explorerPlugin = GraphiQLPluginExplorer.explorerPlugin();
      root.render(
        React.createElement(GraphiQL, {
          fetcher,
          defaultEditorToolsVisibility: true,
          plugins: [explorerPlugin],
        }),
      );
    </script>
  </body>
</html>
"""
