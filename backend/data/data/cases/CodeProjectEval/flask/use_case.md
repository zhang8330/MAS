[
  {
    "use_case_name": "使用 Flask 构建并运行 Web 应用",
    "primary_actor": "Python Web 开发者",
    "secondary_actor": [
      "HTTP 客户端（浏览器/API 调用方）",
      "Werkzeug（WSGI/路由）",
      "Jinja2（模板渲染）",
      "Click（CLI 工具链）"
    ],
    "trigger": "开发者创建 Flask 实例并注册路由后，通过 flask run 或 WSGI server 启动应用",
    "use_case_description": "Flask 提供从请求分发、上下文管理、模板渲染、会话处理到 CLI 与测试支持的一体化微框架能力。",
    "preconditions": [
      "Python 运行环境可用，Flask 及依赖安装完整",
      "应用入口模块可被导入，路由与配置已定义",
      "运行端口与网络资源可访问"
    ],
    "postconditions": [
      "请求被路由到对应视图并返回响应",
      "请求/应用上下文在生命周期内被正确创建与释放",
      "异常、日志、会话与模板输出按配置生效"
    ],
    "main_flow": [
      "1. 开发者初始化 Flask app，加载配置并注册 Blueprint/路由",
      "2. 客户端发送 HTTP 请求进入 wsgi_app",
      "3. 框架创建 AppContext/RequestContext，执行 before_request 等钩子",
      "4. 路由匹配并执行视图函数或 MethodView.dispatch_request",
      "5. 返回值经 make_response 规范化为 Response",
      "6. 执行 after_request/teardown 回调，写入会话与日志",
      "7. 将最终响应返回给客户端"
    ],
    "alternative_flows": [
      "A1：使用 Jinja2 渲染模板（render_template / stream_template）。",
      "A2：使用 flask CLI（run/shell/routes）进行本地运行与诊断。",
      "A3：使用 FlaskClient 与 FlaskCliRunner 进行自动化测试。"
    ],
    "exception_flows": [
      "E1：路由不匹配或方法不允许，返回对应 HTTP 异常响应。",
      "E2：视图或钩子抛出异常，进入 handle_user_exception / handle_exception 流程。",
      "E3：模板加载失败时抛出 TemplateNotFound，并在调试模式给出加载解释信息。"
    ],
    "priority": "High",
    "business_rules": [
      "请求生命周期必须遵循 context push/pop 与 teardown 顺序",
      "配置项优先影响日志、会话、模板与调试行为",
      "Blueprint 注册后其路由与钩子合并到应用级行为"
    ],
    "assumptions": [
      "应用遵循 WSGI 部署或 Flask CLI 启动模式",
      "开发者了解 Flask 上下文和装饰器使用方式",
      "source_mode: source"
    ],
    "other_constraints": [
      "生产环境需外部 WSGI 服务器与反向代理配合",
      "异步视图需通过 ensure_sync/async_to_sync 与运行时策略兼容"
    ]
  }
]
