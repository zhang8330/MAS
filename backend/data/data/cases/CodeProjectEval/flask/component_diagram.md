```mermaid
graph TB
    client["HTTP Client"] --> wsgi["Flask WSGI Entry\napp.wsgi_app / __call__"]

    subgraph runtime["Runtime Core"]
      app["app.py\nFlask"]
      ctx["ctx.py\nAppContext/RequestContext"]
      bp["blueprints.py\nBlueprint"]
      views["views.py\nView/MethodView"]
      wrappers["wrappers.py\nRequest/Response"]
      sessions["sessions.py\nSessionInterface"]
      templating["templating.py\nJinja Rendering"]
      helpers["helpers.py\nurl_for/send_file/flash"]
      logging["logging.py\ncreate_logger"]
      signals["signals.py"]
    end

    subgraph cli_test["CLI & Testing"]
      cli["cli.py\nFlaskGroup/run/shell/routes"]
      testing["testing.py\nFlaskClient/FlaskCliRunner"]
    end

    subgraph jsonpkg["JSON 子系统"]
      jsoninit["json/__init__.py"]
      provider["json/provider.py\nJSONProvider"]
      tag["json/tag.py\nTaggedJSONSerializer"]
    end

    subgraph deps["External"]
      werkzeug["Werkzeug"]
      jinja2["Jinja2"]
      click["Click"]
      blinker["Blinker"]
    end

    wsgi --> app
    app --> ctx
    app --> bp
    app --> wrappers
    app --> sessions
    app --> templating
    app --> helpers
    app --> logging
    app --> signals
    app --> views

    app --> jsoninit
    jsoninit --> provider
    provider --> tag

    cli --> app
    cli --> click
    testing --> app

    wrappers --> werkzeug
    app --> werkzeug
    templating --> jinja2
    signals --> blinker
```