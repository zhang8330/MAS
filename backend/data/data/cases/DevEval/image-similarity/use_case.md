[
  {
    "use_case_name": "批量判断图片相似度（Histogram / PHash）",
    "primary_actor": "开发者或命令行用户",
    "secondary_actor": [
      "文件系统",
      "远程图片 URL"
    ],
    "trigger": "用户执行 Main.main(args) 并传入 input、output、command",
    "use_case_description": "系统读取输入文件中的图片对，按命令 h 或 p 分别调用 ImageHistogram 或 ImagePHash，输出每对图片是否相似。",
    "preconditions": [
      "参数数量为 3",
      "input 文件存在且每行包含两个路径",
      "output 路径可写",
      "当使用 URL 时网络可访问"
    ],
    "postconditions": [
      "输出文件包含每对图片的判断结果和路径",
      "h 模式下基于 score>=0.8 判定",
      "p 模式下基于 distance<10 判定"
    ],
    "main_flow": [
      "1. 用户调用 Main.main(args)",
      "2. 系统读取输入文件逐行解析两个图片路径",
      "3. command=h 时调用 hMatch(path1,path2) -> ImageHistogram.match",
      "4. command!=h 时调用 pMatch(path1,path2) -> ImagePHash.distance",
      "5. 写入结果行到输出文件"
    ],
    "alternative_flows": [
      "A1：某行不含两个路径时打印错误并跳过该行。"
    ],
    "exception_flows": [
      "E1：参数数量不为 3，抛出 IllegalArgumentException。",
      "E2：读写文件发生 IOException，打印异常。",
      "E3：图像解析或 URL 处理异常，包装为 RuntimeException 抛出。"
    ],
    "priority": "High",
    "business_rules": [
      "Histogram 相似度阈值为 0.8",
      "PHash 距离阈值为 10",
      "支持本地文件路径与 http URL 两类输入"
    ],
    "assumptions": [
      "输入图片格式可被 ImageIO 读取",
      "输入文本每行用空格分隔两个路径"
    ],
    "other_constraints": [
      "实现语言为 Java",
      "核心行为需覆盖 unit test 与 acceptance test"
    ]
  }
]
