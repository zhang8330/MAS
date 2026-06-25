[
  {
    "use_case_name": "计算文本/HTML/Markdown 阅读时长",
    "primary_actor": "开发者",
    "secondary_actor": [
      "内容解析器"
    ],
    "trigger": "调用 of_text(text,wpm) / of_html(html,wpm) / of_markdown(markdown,wpm)",
    "use_case_description": "系统根据输入内容类型调用统一 read_time 逻辑，计算并返回阅读时长结果。",
    "preconditions": [
      "输入内容为字符串",
      "wpm 为正整数"
    ],
    "postconditions": [
      "返回 ReadResult 对象",
      "结果包含 seconds 与可读文本"
    ],
    "main_flow": [
      "1. 调用方选择 API（text/html/markdown）",
      "2. API 将 format 与 wpm 透传到 utils.read_time",
      "3. read_time 对内容做解析与词数统计",
      "4. 计算 seconds 并构造 ReadResult",
      "5. 返回结果给调用方"
    ],
    "alternative_flows": [
      "A1：当输入为空文本时，返回最小可表示阅读时长结果。"
    ],
    "exception_flows": [
      "E1：输入内容类型错误时抛出异常。",
      "E2：wpm 非法时抛出异常或返回错误。"
    ],
    "priority": "High",
    "business_rules": [
      "默认 wpm=265",
      "三类输入统一走 read_time 核心逻辑",
      "结果表示由 result 模块负责"
    ],
    "assumptions": [
      "输入内容编码正常可解析",
      "调用方接受秒级阅读时长估算"
    ],
    "other_constraints": [
      "实现语言为 Python",
      "需通过 unit_tests 与 acceptance_tests"
    ]
  }
]
