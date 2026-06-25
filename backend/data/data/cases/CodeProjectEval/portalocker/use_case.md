[
  {
    "use_case_name": "使用 portalocker 实现跨平台文件与分布式锁",
    "primary_actor": "应用开发者/运维脚本",
    "secondary_actor": [
      "操作系统文件锁机制（fcntl/msvcrt/win32）",
      "文件系统",
      "Redis 服务（可选）"
    ],
    "trigger": "调用方创建 Lock/RLock/TemporaryFileLock/PidFileLock 或 RedisLock 并执行 acquire/release",
    "use_case_description": "提供跨平台同步原语，保障多进程/多实例并发场景下对共享资源的互斥访问，支持本地文件锁与 Redis PubSub 分布式锁。",
    "preconditions": [
      "目标路径可访问且具备读写权限",
      "运行环境支持对应锁实现（POSIX 或 Windows API）",
      "若使用 RedisLock，Redis 连接参数与网络可用"
    ],
    "postconditions": [
      "锁成功获取时，调用方可安全执行临界区逻辑",
      "超时或冲突时抛出 AlreadyLocked/LockException 等异常",
      "上下文退出或对象销毁时锁资源被释放并尽量清理临时文件"
    ],
    "main_flow": [
      "1. 调用方实例化锁对象并配置 timeout/check_interval/fail_when_locked",
      "2. 调用 acquire()，框架按超时策略循环尝试加锁",
      "3. 成功后进入临界区读写共享资源",
      "4. 调用 release() 或退出 with 上下文自动解锁",
      "5. 对临时锁/PID 锁执行附加清理（删除锁文件）"
    ],
    "alternative_flows": [
      "A1：使用 RLock 允许同一进程重入并通过计数延迟真正解锁。",
      "A2：使用 BoundedSemaphore/NamedBoundedSemaphore 限制并发持有者数量。",
      "A3：使用 RedisLock 在分布式场景基于 PubSub 维持锁存活与失效检测。",
      "A4：通过 open_atomic 先写临时文件再原子替换目标文件。"
    ],
    "exception_flows": [
      "E1：在超时时间内无法获取锁，抛出 AlreadyLocked。",
      "E2：底层系统调用失败，抛出 LockException 或 BaseLockException。",
      "E3：锁文件过大或状态异常触发 FileToLarge 等扩展异常。",
      "E4：Redis 连接中断导致锁持有状态失效并触发线程/连接清理。"
    ],
    "priority": "High",
    "business_rules": [
      "加锁与解锁必须成对，优先使用上下文管理器保证释放",
      "不同平台采用不同 locker 实现但对外 API 保持一致",
      "分布式锁应可检测失联持有者并具备自愈/回收机制"
    ],
    "assumptions": [
      "调用方可接受锁竞争下的重试与阻塞策略",
      "source_mode: source"
    ],
    "other_constraints": [
      "网络抖动会影响 RedisLock 的可用性和判活时延",
      "Windows 与 POSIX 的锁语义细节存在差异"
    ]
  }
]
