[
  {
    "use_case_name": "生成并格式化许可证文本",
    "primary_actor": "开发者/命令行用户",
    "secondary_actor": [
      "文件系统",
      "git config"
    ],
    "trigger": "用户执行 lice 命令并传入 license/template/language/output 等参数",
    "use_case_description": "系统加载许可证模板，替换变量（year/organization/project），并按指定语言注释风格输出到 stdout 或文件。",
    "preconditions": [
      "模板文件存在（内置或 --template 指定路径）",
      "license 参数在支持列表中或使用默认 bsd3",
      "若指定 language，则必须在 LANGS 映射中"
    ],
    "postconditions": [
      "成功生成替换变量后的许可证文本",
      "若指定输出文件，文本被写入目标路径",
      "若指定 --header，则输出源码头部注释格式"
    ],
    "main_flow": [
      "1. 用户输入命令行参数并执行 main()",
      "2. 系统解析参数并确定 license/template/context",
      "3. 系统加载模板并提取变量",
      "4. 系统调用 generate_license(template, context) 生成文本",
      "5. 若指定语言，系统调用 format_license() 添加注释前后缀",
      "6. 系统输出到 stdout 或写入目标文件"
    ],
    "alternative_flows": [
      "A1：用户使用 --licenses，系统仅列出可用许可证和变量。",
      "A2：用户使用 --languages，系统仅列出支持语言后缀。",
      "A3：用户使用 --vars，系统仅输出模板变量及默认值。"
    ],
    "exception_flows": [
      "E1：language 不受支持，输出错误并退出。",
      "E2：header 模式下模板不存在，输出错误并退出。",
      "E3：模板变量缺失，抛出 ValueError。",
      "E4：模板路径不存在，抛出 ValueError。"
    ],
    "priority": "High",
    "business_rules": [
      "默认许可证为 bsd3",
      "默认 organization 来源于 git config user.name，失败时回退为当前用户",
      "支持按文件扩展名或 -l 参数应用注释格式"
    ],
    "assumptions": [
      "templates 目录存在且包含合法模板文件",
      "命令运行环境有读写权限"
    ],
    "other_constraints": [
      "实现语言为 Python",
      "需通过 unit_tests 与 acceptance_tests"
    ]
  }
]
