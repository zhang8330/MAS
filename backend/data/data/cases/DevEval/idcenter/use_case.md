[
  {
    "use_case_name": "生成并输出 ID（IdWorker / SidWorker）",
    "primary_actor": "开发者或命令行用户",
    "secondary_actor": [
      "文件系统"
    ],
    "trigger": "用户执行 Main.main(args)，并传入子命令、生成数量和输出路径",
    "use_case_description": "系统根据子命令选择 IdWorker 或 SidWorker 生成 ID，并将结果写入指定输出文件。",
    "preconditions": [
      "JVM 运行环境可用",
      "命令行参数包含 subcommand、num、output 三项",
      "输出路径可写"
    ],
    "postconditions": [
      "当 subcommand=idworker 时，输出文件包含两组 IdWorker 生成的 ID 与时间戳",
      "当 subcommand=sidworker 时，输出文件包含 SidWorker 生成的时间序列 ID",
      "非法子命令时输出 usage 信息"
    ],
    "main_flow": [
      "1. 用户输入参数并调用 Main.main(args)",
      "2. 系统解析 subcommand、num、output",
      "3. 若 subcommand 为 idworker，创建 IdWorker 实例并循环调用 getId/getIdTimestamp 写文件",
      "4. 若 subcommand 为 sidworker，循环调用 SidWorker.nextSid 写文件",
      "5. 系统关闭写入流并结束"
    ],
    "alternative_flows": [
      "A1：subcommand 非 idworker/sidworker，输出帮助信息后退出。"
    ],
    "exception_flows": [
      "E1：参数数量不为 3，输出 usage 信息并返回。",
      "E2：文件写入发生 IOException，打印异常堆栈。",
      "E3：IdWorker 构造参数非法，抛出 IllegalArgumentException。"
    ],
    "priority": "High",
    "business_rules": [
      "IdWorker 支持 4 种构造方式，并基于雪花算法生成 long 型 ID",
      "SidWorker.nextSid 生成 19 位时间戳型 ID",
      "Base62 负责 long 与 base62 字符串互转"
    ],
    "assumptions": [
      "系统时钟单调可用",
      "输出文件路径对应目录已存在或可创建"
    ],
    "other_constraints": [
      "实现语言为 Java",
      "核心行为需通过 unit test 与 acceptance test"
    ]
  }
]
