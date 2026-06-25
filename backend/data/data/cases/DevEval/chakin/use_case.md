[
  {
    "use_case_name": "查询并下载词向量数据集",
    "primary_actor": "开发者/终端用户",
    "secondary_actor": [
      "远程数据集下载源"
    ],
    "trigger": "用户调用 search(lang) 或 download(number,name,save_dir)",
    "use_case_description": "系统从 datasets.csv 加载数据集元信息，支持按语言筛选并下载指定编号或名称的数据集文件到本地目录。",
    "preconditions": [
      "datasets.csv 文件存在且可读",
      "网络可访问数据集 URL",
      "save_dir 目录可写"
    ],
    "postconditions": [
      "search 返回匹配数据集列表",
      "download 返回下载文件路径",
      "下载文件保存到指定目录"
    ],
    "main_flow": [
      "1. 用户调用 search(lang) 或 download(number,name,save_dir)",
      "2. 系统调用 load_datasets() 读取 datasets.csv",
      "3. search 按 Language 字段过滤并返回结果",
      "4. download 根据 number 或 name 选中数据集",
      "5. 系统通过 urlretrieve 下载文件并显示进度",
      "6. 返回本地保存路径"
    ],
    "alternative_flows": [
      "A1：lang 为空时，search 返回全部数据集。",
      "A2：download 仅提供 number 或仅提供 name，仍可匹配并下载。"
    ],
    "exception_flows": [
      "E1：number 与 name 同时为空或同时提供，抛出 ValueError。",
      "E2：指定 number/name 不存在，抛出 ValueError。",
      "E3：save_dir 不存在，抛出 IOError。",
      "E4：下载失败（网络或 URL 异常），抛出 urllib 相关异常。"
    ],
    "priority": "High",
    "business_rules": [
      "download 参数 number 与 name 必须二选一",
      "结果数据源以 datasets.csv 为准",
      "search 过滤依据为 Language 字段"
    ],
    "assumptions": [
      "datasets.csv 列结构稳定（包含 Name/Language/URL）",
      "运行环境具备 urllib 和 progressbar 依赖"
    ],
    "other_constraints": [
      "实现语言为 Python",
      "行为需与 unit_tests 和 acceptance_tests 一致"
    ]
  }
]
