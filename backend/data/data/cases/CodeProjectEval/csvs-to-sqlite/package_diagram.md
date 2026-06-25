```mermaid
graph TD
    subgraph pkg["csvs_to_sqlite 包"]
      init["__init__.py"]
      cli["cli.py"]
      utils["utils.py"]
    end

    subgraph ext["外部依赖"]
      click["click"]
      pandas["pandas"]
      sqlite3["sqlite3"]
      lru["lru"]
      dateparser["dateparser"]
      six["six"]
    end

    init --> cli
    cli --> utils
    cli --> click

    utils --> pandas
    utils --> sqlite3
    utils --> lru
    utils --> dateparser
    utils --> six
```