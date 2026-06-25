[
  {
    "use_case_name": "使用 csvs-to-sqlite 将 CSV 批量导入 SQLite",
    "primary_actor": "数据工程师/命令行用户",
    "secondary_actor": [
      "本地文件系统或 URL 数据源",
      "SQLite 数据库引擎",
      "Pandas 与 dateparser 解析组件"
    ],
    "trigger": "用户执行 csvs-to-sqlite PATHS... DBNAME 命令",
    "use_case_description": "将一个或多个 CSV/TSV 文件解析为 DataFrame，经字段映射与类型处理后写入 SQLite，并可附加外键抽取、索引与 FTS。",
    "preconditions": [
      "Python 环境可用且依赖安装完整（click/pandas/dateparser 等）",
      "输入路径可访问（文件、目录或 URL）",
      "输出数据库文件路径具备写权限"
    ],
    "postconditions": [
      "目标 SQLite 数据库创建成功并包含导入表",
      "可选索引、外键约束和 FTS 虚拟表被创建",
      "失败场景返回明确异常或命令行错误提示"
    ],
    "main_flow": [
      "1. CLI 解析参数（分隔符、shape、日期列、索引、FTS、replace 等）",
      "2. 扫描 PATHS 生成待导入表名与 CSV 路径映射（csvs_from_paths）",
      "3. 逐个文件加载为 DataFrame（load_csv），并应用 shape/date/datetime/fixed-column 规则",
      "4. 根据 extract-column 规则抽取维表并回填外键 ID（refactor_dataframes）",
      "5. 生成建表 SQL 并写入主表数据（to_sql_with_foreign_keys）",
      "6. 按需创建普通索引和全文检索表（add_index / generate_and_populate_fts）",
      "7. 输出处理结果，结束命令"
    ],
    "alternative_flows": [
      "A1：启用 --just-strings，默认按文本导入（仍可叠加 shape 与日期解析）。",
      "A2：启用 --replace-tables，已存在表会先删除再重建。",
      "A3：启用 --skip-errors，遇到坏行时跳过而非终止。"
    ],
    "exception_flows": [
      "E1：CSV 编码或格式不兼容导致 load_csv 失败，抛出 LoadCsvError。",
      "E2：shape 或索引字段配置不合法，触发 ValueError/SQLite 错误。",
      "E3：数据库写入失败（锁冲突、约束冲突等）导致导入中断。"
    ],
    "priority": "High",
    "business_rules": [
      "表名默认由输入文件名推导，冲突时自动追加后缀",
      "外键抽取列以 lookup table 形式标准化并回填整数 ID",
      "FTS 版本按运行环境能力自动选择（优先 FTS5）"
    ],
    "assumptions": [
      "输入数据以表格型 CSV/TSV 为主，列头可解析",
      "source_mode: source"
    ],
    "other_constraints": [
      "超大 CSV 导入耗时与内存占用受 Pandas 读取策略影响",
      "不同 SQLite 版本对 FTS 能力支持存在差异"
    ]
  }
]
