[
  {
    "use_case_name": "使用 TinyDB 进行轻量文档存储与查询",
    "primary_actor": "应用开发者/脚本程序",
    "secondary_actor": [
      "存储后端（JSONStorage/MemoryStorage）",
      "中间件（CachingMiddleware）",
      "查询表达式系统（Query/where）"
    ],
    "trigger": "调用方创建 TinyDB 实例并执行 insert/search/update/remove 等操作",
    "use_case_description": "在本地文件或内存中维护 JSON 文档数据库，按表组织数据并提供链式查询、批量更新与 upsert 能力，适用于嵌入式与小型应用场景。",
    "preconditions": [
      "数据库路径可访问（文件模式）或内存实例可用",
      "写入文档可序列化为 JSON（使用 JSONStorage 时）",
      "查询条件与文档结构匹配"
    ],
    "postconditions": [
      "文档被写入、更新、删除或检索成功",
      "表级数据与文档 ID 保持一致性",
      "缓存与存储状态在关闭时正确落盘（若启用缓存中间件）"
    ],
    "main_flow": [
      "1. 初始化 TinyDB，配置 storage/middleware/table_class",
      "2. 获取默认表或命名表（table(name)）",
      "3. 执行 insert/insert_multiple 写入文档",
      "4. 通过 Query/where 构建条件并执行 search/get/contains",
      "5. 使用 update/upsert/remove/truncate 修改数据",
      "6. close() 关闭数据库并释放底层资源"
    ],
    "alternative_flows": [
      "A1：使用 MemoryStorage 在测试或临时场景中纯内存运行。",
      "A2：使用 CachingMiddleware 批量缓存写入，降低磁盘 I/O 频率。",
      "A3：通过 operations.add/set/delete 等函数式更新器实现字段级变更。"
    ],
    "exception_flows": [
      "E1：JSON 反序列化失败导致读取异常（文件损坏或格式非法）。",
      "E2：访问模式配置不当（如危险写模式）导致数据覆盖或警告。",
      "E3：查询或更新条件不匹配时返回空结果集合（逻辑层需处理）。"
    ],
    "priority": "High",
    "business_rules": [
      "每个表内 doc_id 必须唯一且由表维护递增分配",
      "查询缓存仅对可哈希且可缓存的 QueryInstance 生效",
      "drop_table/drop_tables 属于不可逆破坏性操作"
    ],
    "assumptions": [
      "数据规模与并发需求适配 TinyDB 的轻量定位",
      "source_mode: source"
    ],
    "other_constraints": [
      "默认实现不强调多进程并发写一致性",
      "大数据量场景下全量读写与 JSON 序列化会产生性能瓶颈"
    ]
  }
]
