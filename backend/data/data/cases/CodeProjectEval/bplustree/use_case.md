[
  {
    "use_case_name": "使用 bplustree 进行持久化键值存储与查询",
    "primary_actor": "开发者/应用服务",
    "secondary_actor": [
      "文件系统",
      "Write-Ahead Log (WAL)",
      "可选序列化组件（temporenc）"
    ],
    "trigger": "调用方创建 BPlusTree 实例并执行 insert/get/items 等 API",
    "use_case_description": "基于磁盘页与 WAL 的 B+Tree，支持键值插入、查询、范围遍历、检查点落盘与崩溃恢复。",
    "preconditions": [
      "Python 运行环境可用，依赖安装完整（cachetools、rwlock 等）",
      "数据文件路径可访问并具备读写权限",
      "key/value 满足 TreeConf 的 key_size、value_size 和序列化约束"
    ],
    "postconditions": [
      "写入事务通过 WAL 提交，数据可在 checkpoint 后持久化到主数据文件",
      "查询返回目标 value 或 default 值",
      "关闭树实例后句柄被正确释放"
    ],
    "main_flow": [
      "1. 调用方初始化 BPlusTree（加载 metadata 或创建空树）",
      "2. 执行写操作（insert/batch_insert），系统在 write_transaction 中修改节点并写 WAL",
      "3. 若节点满则触发分裂（叶子或内部节点），必要时创建新根",
      "4. 执行读操作（get/items/values），系统在 read_transaction 中检索目标记录",
      "5. 对超大 value 通过 overflow pages 存取并重组",
      "6. 调用 checkpoint/close，完成 WAL 检查点与资源回收"
    ],
    "alternative_flows": [
      "A1：insert 遇到已存在 key 且 replace=False，抛出 ValueError。",
      "A2：调用 __getitem__ 访问不存在 key，抛出 KeyError。",
      "A3：batch_insert 输入非升序或与现有键冲突，抛出 ValueError。"
    ],
    "exception_flows": [
      "E1：I/O 异常或事务异常时，WAL rollback 并清理未提交页。",
      "E2：序列化器不可用（如 DatetimeUTCSerializer 缺少 temporenc）时抛出 RuntimeError。",
      "E3：页面读取越界时触发 ReachedEndOfFile。"
    ],
    "priority": "High",
    "business_rules": [
      "B+Tree 节点始终保持有序与平衡约束",
      "写路径先记录 WAL，再提交，保证崩溃一致性",
      "叶子节点按 next_page 串联以支持范围扫描"
    ],
    "assumptions": [
      "运行在本地文件系统（Windows/Linux/macOS）",
      "source_mode: source"
    ],
    "other_constraints": [
      "page_size、order 等参数需与底层实现约束一致",
      "大 value 可能引入 overflow 页与额外 I/O 开销"
    ]
  }
]
