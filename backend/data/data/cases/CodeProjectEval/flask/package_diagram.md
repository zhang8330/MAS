```mermaid
graph TD
    subgraph public_api["Public API"]
      init["__init__.py"]
      app["app.py"]
      bp["blueprints.py"]
      helpers["helpers.py"]
      views["views.py"]
      cli["cli.py"]
    end

    subgraph core_runtime["Runtime Core"]
      sansio_app["sansio/app.py"]
      sansio_bp["sansio/blueprints.py"]
      sansio_scaffold["sansio/scaffold.py"]
      ctx["ctx.py"]
      wrappers["wrappers.py"]
      sessions["sessions.py"]
      config["config.py"]
      templating["templating.py"]
      logging_mod["logging.py"]
      signals["signals.py"]
      globals["globals.py"]
      debughelpers["debughelpers.py"]
      typing["typing.py"]
    end

    subgraph jsonpkg["JSON Package"]
      json_init["json/__init__.py"]
      json_provider["json/provider.py"]
      json_tag["json/tag.py"]
    end

    subgraph testingpkg["Testing"]
      testing["testing.py"]
    end

    subgraph deps["External Dependencies"]
      werkzeug["Werkzeug"]
      jinja2["Jinja2"]
      click["Click"]
      blinker["Blinker"]
      itsdangerous["itsdangerous"]
    end

    init --> app
    init --> bp
    init --> helpers
    init --> views

    app --> sansio_app
    bp --> sansio_bp
    sansio_app --> sansio_scaffold
    sansio_bp --> sansio_scaffold

    app --> ctx
    app --> wrappers
    app --> sessions
    app --> config
    app --> templating
    app --> logging_mod
    app --> signals
    app --> globals
    app --> debughelpers

    app --> json_init
    json_init --> json_provider
    json_provider --> json_tag

    cli --> app
    cli --> click
    testing --> app

    wrappers --> werkzeug
    app --> werkzeug
    templating --> jinja2
    sessions --> itsdangerous
    signals --> blinker
```