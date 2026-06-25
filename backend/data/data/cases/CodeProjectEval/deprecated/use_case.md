[
  {
    "use_case_name": "在 Python 代码中标注弃用 API",
    "primary_actor": "Python 开发者",
    "secondary_actor": [
      "Python warnings 子系统",
      "Sphinx 文档构建流程",
      "wrapt 装饰器适配层"
    ],
    "trigger": "开发者在函数/方法/类上添加 @deprecated、@versionadded 或 @versionchanged 装饰器",
    "use_case_description": "通过 deprecated 库在运行时发出弃用警告，并可同步向 docstring 注入 Sphinx 指令，帮助 API 演进和兼容迁移。",
    "preconditions": [
      "运行环境为 Python，且可导入 deprecated 包",
      "目标对象为可装饰的函数、方法或类",
      "若使用 Sphinx 指令，需提供版本号并遵循文档构建约定"
    ],
    "postconditions": [
      "被标注对象保留原有调用行为",
      "调用时按策略发出 DeprecationWarning（或指定类别）",
      "docstring 可追加 versionadded/versionchanged/deprecated 指令"
    ],
    "main_flow": [
      "1. 开发者选择 classic.deprecated 或 sphinx.* 装饰器并配置 reason/version",
      "2. 装饰器创建 Adapter（ClassicAdapter 或 SphinxAdapter）包装目标对象",
      "3. 目标对象被调用时，适配器生成并发出警告信息",
      "4. 若为 SphinxAdapter，文档字符串被写入对应 Sphinx directive",
      "5. 调用方继续获得原函数/类的执行结果"
    ],
    "alternative_flows": [
      "A1：仅使用 versionadded/versionchanged，仅修改 docstring，不发运行时弃用警告。",
      "A2：通过 action/category 调整 warnings 过滤行为与警告类型。",
      "A3：通过 adapter_cls 自定义适配器逻辑。"
    ],
    "exception_flows": [
      "E1：SphinxAdapter 在缺少必填 directive/version 时参数校验失败。",
      "E2：被装饰对象类型不符合预期时，包装行为可能不生效或抛出类型相关异常。"
    ],
    "priority": "High",
    "business_rules": [
      "弃用信息应包含对象类型、名称、原因与版本",
      "警告默认遵循 Python warnings 机制，不强制中断执行",
      "Sphinx 语法应与运行时警告文案保持可读一致"
    ],
    "assumptions": [
      "调用方理解弃用策略并会处理迁移",
      "source_mode: source"
    ],
    "other_constraints": [
      "不同运行环境下 warnings 过滤配置可能影响可见性",
      "文档注入效果依赖 Sphinx 对应主题和构建链路"
    ]
  }
]
