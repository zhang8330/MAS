[
  {
    "use_case_name": "使用 cookiecutter 从模板生成项目",
    "primary_actor": "开发者/CLI 用户",
    "secondary_actor": [
      "本地文件系统",
      "远程代码仓库（Git/Hg/Zip）",
      "Jinja2 模板引擎",
      "Hook 脚本运行环境"
    ],
    "trigger": "用户通过命令行或 Python API 调用 cookiecutter.main.cookiecutter()",
    "use_case_description": "根据模板仓库与上下文变量生成项目脚手架，支持交互式输入、replay、hooks 与多种模板来源。",
    "preconditions": [
      "Python 环境与 cookiecutter 依赖可用（click、jinja2、pyyaml、requests 等）",
      "模板来源可访问（本地路径、Git/Hg 仓库或 Zip）",
      "目标输出目录具备创建与写入权限"
    ],
    "postconditions": [
      "目标目录生成渲染后的项目文件",
      "可选地写入 replay 文件用于后续复现生成",
      "日志与错误信息可追踪"
    ],
    "main_flow": [
      "1. 入口解析参数并加载用户配置（config/get_user_config）",
      "2. 解析模板来源并定位仓库目录（repository/determine_repo_dir）",
      "3. 读取 cookiecutter.json 并合并 default_context/extra_context（generate_context）",
      "4. 交互或 no-input/replay 方式获取最终上下文（prompt/replay）",
      "5. 创建 Jinja2 严格环境并渲染目录与文件（generate_files/generate_file）",
      "6. 按策略执行 pre/post hooks（hooks）",
      "7. 返回生成项目路径并完成临时资源清理"
    ],
    "alternative_flows": [
      "A1：启用 --no-input，直接使用默认值与 extra_context，不进行交互提示。",
      "A2：启用 --replay 或 --replay-file，直接加载历史上下文生成。",
      "A3：目标目录已存在且允许 overwrite/skip-if-file-exists 时按策略覆盖或跳过。"
    ],
    "exception_flows": [
      "E1：模板仓库不可达或克隆失败，抛出 RepositoryNotFound/RepositoryCloneFailed。",
      "E2：cookiecutter.json 非法，抛出 ContextDecodingException。",
      "E3：模板渲染出现未定义变量，抛出 UndefinedVariableInTemplate。",
      "E4：Hook 执行失败，抛出 FailedHookException 并按配置清理已生成目录。"
    ],
    "priority": "High",
    "business_rules": [
      "模板目录必须可识别且满足 cookiecutter 约定",
      "上下文变量渲染采用 StrictUndefined，未定义变量视为错误",
      "hooks 执行策略由 accept_hooks 与运行模式共同决定"
    ],
    "assumptions": [
      "用户具备基本命令行操作能力",
      "运行环境允许子进程执行 hook 脚本",
      "source_mode: source"
    ],
    "other_constraints": [
      "跨平台支持 Windows/macOS/Linux，部分权限行为受平台差异影响",
      "远程下载/克隆能力受网络与凭据配置影响"
    ]
  }
]
