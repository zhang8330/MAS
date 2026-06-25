[
  {
    "use_case_name": "通过 IMAPClient 连接邮箱并执行邮件操作",
    "primary_actor": "Python 开发者/自动化任务",
    "secondary_actor": [
      "IMAP 邮件服务器",
      "TLS/SSL 网络栈",
      "OAuth2 提供方（可选）"
    ],
    "trigger": "调用方创建 IMAPClient 实例并执行 login/select/search/fetch/append 等方法",
    "use_case_description": "提供面向 IMAP 协议的高级 Python API，支持认证、文件夹管理、邮件检索、标记修改、拷贝移动、配额查询和响应解析。",
    "preconditions": [
      "网络可达目标 IMAP 服务器",
      "服务器支持所需能力（如 IDLE、UIDPLUS、MOVE、QUOTA、STARTTLS）",
      "用户名密码或 OAuth2 凭据有效"
    ],
    "postconditions": [
      "成功执行 IMAP 操作并返回结构化结果（如 Envelope、SearchIds）",
      "连接会话可保持或按上下文管理器安全退出",
      "失败时抛出明确异常并保留调试线索"
    ],
    "main_flow": [
      "1. 根据配置创建 IMAPClient（SSL/TLS、超时、UID 策略）",
      "2. 执行 login/oAuth 登录并读取 capabilities",
      "3. 选择目标邮箱（select_folder）并发起 search/sort/thread",
      "4. 对命中邮件执行 fetch，响应经 lexer/parser 转换为结构化对象",
      "5. 业务按需执行 flag/label 修改、copy/move/append/expunge",
      "6. 可选使用 idle/idle_check 实现实时事件监听",
      "7. 退出时 logout 或 shutdown 释放连接"
    ],
    "alternative_flows": [
      "A1：通过 config.create_client_from_config 从配置文件与环境变量快速建连。",
      "A2：服务器支持 STARTTLS 时，先明文连接后升级 TLS。",
      "A3：使用 TestableIMAPClient/MockIMAP4 在测试环境模拟协议交互。"
    ],
    "exception_flows": [
      "E1：认证失败触发 LoginError 或服务器错误响应。",
      "E2：缺少能力时触发 CapabilityError（由 require_capability 装饰器拦截）。",
      "E3：服务器响应格式异常时触发 ProtocolError/解析异常。",
      "E4：网络超时或连接中断导致 socket/IMAP 层异常。"
    ],
    "priority": "High",
    "business_rules": [
      "命令执行前需校验服务器能力与当前会话状态",
      "敏感认证日志应脱敏（IMAPlibLoggerAdapter）",
      "文件夹名称按 IMAP UTF-7 进行编码/解码"
    ],
    "assumptions": [
      "调用方具备基础 IMAP 协议认知",
      "邮箱服务端遵循 RFC3501 及相关扩展",
      "source_mode: source"
    ],
    "other_constraints": [
      "不同厂商 IMAP 扩展能力存在差异（如 Gmail X-GM-EXT-1）",
      "大批量 fetch/search 可能带来明显网络与解析开销"
    ]
  }
]
