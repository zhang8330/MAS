[
  {
    "use_case_name": "将 CSV 转换为嵌套 JSON",
    "primary_actor": "开发者/终端用户",
    "secondary_actor": [
      "文件系统"
    ],
    "trigger": "用户调用 Hone.convert(csv_filepath, schema=None)",
    "use_case_description": "系统读取 CSV 列名与数据行，自动推导或使用给定 schema，生成嵌套 JSON 结构并返回。",
    "preconditions": [
      "CSV 文件存在且可读取",
      "列名与数据行格式合法",
      "若提供 schema，则与列名语义兼容"
    ],
    "postconditions": [
      "返回 JSON 列表结构（每一行对应一个 JSON 对象）",
      "可选地通过 json_utils.output_json 输出到文件"
    ],
    "main_flow": [
      "1. 调用 Hone.convert(csv_filepath, schema)",
      "2. CSVUtils 读取列名与数据行",
      "3. 若 schema 为空，执行 generate_full_structure 自动推导嵌套结构",
      "4. 执行 populate_structure_with_data 将每行数据填充到结构",
      "5. 返回最终 JSON 结构"
    ],
    "alternative_flows": [
      "A1：调用 Hone.get_schema(csv_filepath) 仅获取推导 schema，不进行数据填充。"
    ],
    "exception_flows": [
      "E1：CSV 路径无效或读取失败，抛出文件访问异常。",
      "E2：列名与数据不匹配导致填充失败，转换流程终止。"
    ],
    "priority": "High",
    "business_rules": [
      "默认分隔符为 [',', '_', ' ']",
      "列名前缀关系用于推导嵌套层级",
      "数据填充前需执行引号转义"
    ],
    "assumptions": [
      "输入 CSV 首行为列名",
      "每行字段数量与列名数量一致"
    ],
    "other_constraints": [
      "实现语言为 Python",
      "行为需通过 unit_tests 与 acceptance_tests 验证"
    ]
  }
]
