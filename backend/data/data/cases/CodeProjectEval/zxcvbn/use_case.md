[
  {
    "use_case_name": "评估密码强度并输出可执行改进建议",
    "primary_actor": "应用开发者/终端用户",
    "secondary_actor": [
      "密码创建界面（Web/App）",
      "策略引擎（注册/重置密码流程）",
      "命令行调用环境"
    ],
    "trigger": "调用方执行 zxcvbn(password, user_inputs) 或 CLI 输入密码进行评估",
    "use_case_description": "zxcvbn 通过模式匹配与猜测成本估算分析密码可破解性，输出分数、攻击时间估计、匹配序列与反馈建议，辅助前端实时提示与后端策略判定。",
    "preconditions": [
      "输入密码为可处理字符串",
      "可选 user_inputs（用户名、邮箱、姓名等）已标准化",
      "内置词频字典与键盘邻接图可用"
    ],
    "postconditions": [
      "返回包含 score、guesses、attack_times、feedback、sequence 的评估结果",
      "业务可据此决定通过、拦截或二次提示",
      "评估过程不存储明文密码（由调用方负责生命周期控制）"
    ],
    "main_flow": [
      "1. 接收密码及可选用户上下文词典输入",
      "2. matching.omnimatch 运行字典、l33t、键盘路径、重复、序列、日期等匹配器",
      "3. scoring.most_guessable_match_sequence 使用动态规划求解最小猜测代价序列",
      "4. time_estimates 将 guesses 映射为多攻击场景耗时与 score",
      "5. feedback 基于得分和关键匹配生成警告与改进建议",
      "6. 返回结构化 JSON 结果"
    ],
    "alternative_flows": [
      "A1：通过 __main__.py CLI 从 stdin 或 getpass 输入密码并输出 JSON。",
      "A2：注入 user_inputs 提升对个人信息相关弱口令的识别能力。",
      "A3：仅消费 score/guesses 指标，不展示完整匹配细节。"
    ],
    "exception_flows": [
      "E1：输入类型异常导致匹配阶段失败（调用侧需保证类型）。",
      "E2：自定义序列化对象不可直接 JSON 编码，需回退字符串表示。",
      "E3：极端长密码导致计算开销上升，响应时间变长。"
    ],
    "priority": "High",
    "business_rules": [
      "评分应基于猜测次数阈值而非单一长度规则",
      "匹配模式越可预测，估计 guesses 越低",
      "反馈内容应可操作且与最关键弱点模式相关"
    ],
    "assumptions": [
      "攻击模型与 guesses 阈值采用 zxcvbn 既定经验参数",
      "source_mode: source"
    ],
    "other_constraints": [
      "不同语言和本地化词典覆盖度会影响评估准确性",
      "离线场景下无法依赖外部服务进行补充校验"
    ]
  }
]
