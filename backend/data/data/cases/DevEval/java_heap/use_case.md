[
  {
    "use_case_name": "使用 java_heap 的核心功能",
    "primary_actor": "开发者/终端用户",
    "secondary_actor": [
      "系统服务",
      "外部依赖组件"
    ],
    "trigger": "调用方触发 java_heap 的主要功能入口",
    "use_case_description": "# Introduction",
    "preconditions": [
      "系统可用",
      "依赖可访问",
      "输入满足基本合法性"
    ],
    "postconditions": [
      "返回执行结果",
      "记录必要日志",
      "异常场景返回明确错误"
    ],
    "main_flow": [
      "1. 调用方提交请求",
      "2. 系统参数校验",
      "3. 执行核心逻辑",
      "4. 返回结果"
    ],
    "alternative_flows": [
      "A1：参数补全后重试。"
    ],
    "exception_flows": [
      "E1：输入不合法时返回错误。",
      "E2：依赖异常时记录并返回错误。"
    ],
    "priority": "High",
    "business_rules": [
      "输入需校验",
      "处理过程可追踪",
      "错误信息可理解"
    ],
    "assumptions": [
      "运行环境满足最低要求",
      "图文档来源模式：source"
    ],
    "other_constraints": [
      "响应性能满足基本要求",
      "与现有约束兼容"
    ]
  }
]