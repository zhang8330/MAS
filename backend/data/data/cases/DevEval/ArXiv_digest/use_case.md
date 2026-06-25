[
  {
    "use_case_name": "按检索条件获取并输出近期 ArXiv 论文",
    "primary_actor": "命令行用户",
    "secondary_actor": [
      "arXiv API"
    ],
    "trigger": "用户执行 query_arxiv.py 并传入检索参数与 recent_days",
    "use_case_description": "系统构建 arXiv 查询 URL，拉取 XML 数据，按日期过滤近期论文，并打印或导出为 CSV。",
    "preconditions": [
      "至少提供 category/title/author/abstract 之一",
      "参数仅包含允许的 ASCII 字符",
      "网络可访问 export.arxiv.org"
    ],
    "postconditions": [
      "返回并输出满足 recent_days 的论文集合",
      "to_file 非空时写入 UTF-8 CSV",
      "verbose 或未写文件时打印论文摘要信息"
    ],
    "main_flow": [
      "1. 解析命令行参数 get_args(argv)",
      "2. 调用 construct_query_url(...) 生成查询 URL",
      "3. 调用 fetch_data(query_url) 获取 XML",
      "4. 调用 process_entries(...) 解析并按 check_date(...) 过滤",
      "5. 根据参数调用 save_to_csv(...) 和/或 print_results(...)"
    ],
    "alternative_flows": [
      "A1：无论文命中时输出提示 No papers found with the given query parameters。"
    ],
    "exception_flows": [
      "E1：未提供任何检索条件时 construct_query_url 抛 ValueError。",
      "E2：检索参数含非法字符时 construct_query_url 抛 ValueError。",
      "E3：网络或 XML 解析异常导致流程中断。"
    ],
    "priority": "High",
    "business_rules": [
      "查询排序必须为 submittedDate 降序",
      "max_results 默认值为 100",
      "摘要打印时最多展示前 300 个词"
    ],
    "assumptions": [
      "arXiv API 返回 Atom XML 且字段完整",
      "published 字段使用 %Y-%m-%dT%H:%M:%SZ 格式"
    ],
    "other_constraints": [
      "实现语言为 Python",
      "行为需覆盖 unit_tests 与 acceptance_tests"
    ]
  }
]
