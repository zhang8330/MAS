[
  {
    "use_case_name": "使用 parsel 对 HTML/XML/JSON 进行结构化提取",
    "primary_actor": "爬虫开发者/数据处理脚本",
    "secondary_actor": [
      "lxml 解析引擎",
      "cssselect 与 JMESPath 解析器",
      "正则与实体解码工具"
    ],
    "trigger": "调用方创建 Selector 并执行 xpath/css/jmespath/re/get 等提取方法",
    "use_case_description": "提供统一选择器接口，在 HTML/XML/JSON 文本上进行 XPath、CSS、JMESPath 与正则抽取，并支持节点删除、命名空间处理和伪元素语义。",
    "preconditions": [
      "输入文本或字节流可被解析为 HTML/XML/JSON 之一",
      "依赖库可用（lxml、cssselect、jmespath、w3lib）",
      "查询表达式语法满足对应解析器要求"
    ],
    "postconditions": [
      "返回 Selector/SelectorList 或字符串匹配结果",
      "可选地对节点树执行 drop/remove_namespaces 等结构操作",
      "错误场景抛出明确异常（如无父节点删除、非法表达式）"
    ],
    "main_flow": [
      "1. 调用方构建 Selector（自动识别 html/xml/json 或显式指定 type）",
      "2. 通过 xpath/css/jmespath 选择目标节点或值",
      "3. 结果封装为 SelectorList 并可继续链式查询",
      "4. 使用 get/getall/re/re_first 输出文本或匹配结果",
      "5. 如需结构修改，可调用 drop/remove_namespaces",
      "6. 返回抽取数据供上层业务使用"
    ],
    "alternative_flows": [
      "A1：CSS 查询通过 csstranslator 转为 XPath，支持 ::text 与 ::attr(...) 伪元素。",
      "A2：JSON 数据通过 jmespath 查询后再包装为 SelectorList。",
      "A3：调用 xpathfuncs.setup 注册 has-class 扩展函数增强 XPath 语义。"
    ],
    "exception_flows": [
      "E1：对无父节点或无根节点对象调用 drop 时抛出 CannotDropElementWithoutParent/CannotRemoveElementWithoutRoot。",
      "E2：输入文档格式不合法导致解析失败（lxml/json 解析异常）。",
      "E3：表达式非法导致 XPath/CSS/JMESPath 解析异常。"
    ],
    "priority": "High",
    "business_rules": [
      "同一 Selector API 需统一支持 html/xml/json 三类输入",
      "批量查询结果默认以 SelectorList 扁平化返回",
      "文本抽取时可按配置进行 HTML 实体替换"
    ],
    "assumptions": [
      "调用方了解 XPath/CSS/JMESPath 至少一种查询语言",
      "source_mode: source"
    ],
    "other_constraints": [
      "超大文档解析性能依赖 lxml huge_tree 与内存容量",
      "复杂 CSS/JMESPath 表达式可能引入明显计算开销"
    ]
  }
]
