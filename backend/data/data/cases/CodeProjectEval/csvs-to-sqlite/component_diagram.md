```mermaid
graph TB
    user["CLI 用户"] --> cli["cli.py\n命令参数入口"]

    subgraph core["csvs_to_sqlite 核心"]
      utils["utils.py\n数据加载/转换/入库"]
      lookup["LookupTable\n维表与外键映射"]
      pathorurl["PathOrURL\n路径/URL 参数类型"]
    end

    subgraph runtime["运行时依赖"]
      pandas["pandas\nDataFrame 读取与处理"]
      sqlite["sqlite3\n数据库写入"]
      dateparser["dateparser\n日期解析"]
      lru["py-lru-cache\n值到ID缓存"]
      click["click\n参数解析"]
    end

    subgraph io["输入输出"]
      csvsrc[("CSV/TSV 文件或目录/URL")]
      db[("SQLite DB 文件")]
    end

    user --> click
    click --> cli
    cli --> pathorurl
    cli --> utils

    csvsrc --> utils
    utils --> pandas
    utils --> sqlite
    utils --> dateparser
    utils --> lookup
    lookup --> lru
    utils --> db
```