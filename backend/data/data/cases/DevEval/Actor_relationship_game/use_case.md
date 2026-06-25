[
  {
    "use_case_name": "生成演员关系图并查询演员关系路径",
    "primary_actor": "用户",
    "secondary_actor": [
      "TMDB API"
    ],
    "trigger": "用户依次执行图构建、演员列表导出和关系查询命令",
    "use_case_description": "系统从 TMDB API 拉取热门演员与电影信息，构建 ActorGraph，导出演员列表，并计算任意两位演员之间的最短关系路径。",
    "preconditions": [
      "环境变量 TMDB_API_KEY 已设置",
      "网络可访问 TMDB API",
      "输入输出文件路径可读写"
    ],
    "postconditions": [
      "生成 actorGraph.ser 序列化文件",
      "生成 actors_list.txt 演员名单",
      "生成 actor_connection_results.txt 演员关系结果"
    ],
    "main_flow": [
      "1. 用户执行 GraphCreation.createGraph(fileName) 生成图并序列化保存",
      "2. 用户执行 ActorGraphUtil.loadGraph(graphPath) 加载图",
      "3. 用户执行 ActorGraphUtil.writeActorsToFile(actorNames, filePath) 导出演员列表",
      "4. 用户执行 GameplayInterface.loadGraph(fileName) 加载图",
      "5. 用户执行 GameplayInterface.findConnections(actorPairs, outputFilePath) 计算并输出关系路径"
    ],
    "alternative_flows": [
      "A1：若某对演员无连接路径，则输出 No connection found。"
    ],
    "exception_flows": [
      "E1：TMDB API 返回错误或网络异常，图构建终止并报错。",
      "E2：输入文件不存在或格式异常，查询流程报错。",
      "E3：序列化文件读写失败，流程终止并报错。"
    ],
    "priority": "High",
    "business_rules": [
      "演员和电影以 id 唯一标识",
      "关系路径基于 ActorGraph.findConnectionWithPath 计算",
      "输出文件按命令行参数指定路径写入"
    ],
    "assumptions": [
      "TMDB API 返回数据结构符合项目解析逻辑",
      "演员名称在图中可映射到唯一 actorId"
    ],
    "other_constraints": [
      "实现语言为 Java",
      "使用序列化持久化 ActorGraph"
    ]
  }
]
