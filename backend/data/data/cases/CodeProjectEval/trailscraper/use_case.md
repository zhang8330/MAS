[
  {
    "use_case_name": "基于 CloudTrail 记录自动生成最小 IAM 策略",
    "primary_actor": "云安全工程师/平台开发者",
    "secondary_actor": [
      "AWS S3（CloudTrail 日志桶）",
      "AWS CloudTrail LookupEvents API",
      "IAM 策略消费系统（控制台/CI/CD）"
    ],
    "trigger": "调用方执行 trailscraper CLI 的 download/select/generate/guess 子命令",
    "use_case_description": "trailscraper 从 CloudTrail 历史行为中提取实际调用的 API 动作，转换并归并为可落地的最小权限 IAM Policy，同时支持对常见关联权限进行智能补全。",
    "preconditions": [
      "已配置可读取 CloudTrail 的 AWS 凭据",
      "本地日志目录或 CloudTrail API 查询权限可用",
      "输入时间范围、账号、区域参数有效"
    ],
    "postconditions": [
      "下载并筛选得到目标时间窗口内的 CloudTrail 记录",
      "生成结构化 IAM PolicyDocument（Statement 合并去重）",
      "可选输出扩展策略（guess）供人工审阅与落地"
    ],
    "main_flow": [
      "1. 使用 download 从 S3 按账号/区域/时间下载 CloudTrail 日志",
      "2. 使用 select 从本地目录或 CloudTrail API 读取并筛选 Record",
      "3. 将 Record 转换为 IAM Statement（action/resource/effect）",
      "4. policy_generator 对语句按资源与动作维度归并压缩",
      "5. 输出标准 IAM JSON 策略并交付给调用方"
    ],
    "alternative_flows": [
      "A1：跳过本地日志，直接使用 CloudTrailAPIRecordSource 拉取近时间窗口事件。",
      "A2：使用 guess 子命令基于已观察动作补充 Describe/List/Get 等关联权限。",
      "A3：使用 last-event-timestamp 快速判断本地日志是否覆盖到目标时间。"
    ],
    "exception_flows": [
      "E1：S3 下载或 API 拉取失败导致记录不完整。",
      "E2：日志文件损坏/格式异常导致解析 Record 失败并被过滤。",
      "E3：筛选条件过严导致无匹配记录，策略为空或仅保留最小骨架。",
      "E4：未知服务或动作映射不完整导致部分 Statement 无法精确推断。"
    ],
    "priority": "High",
    "business_rules": [
      "策略生成以观察到的真实调用为准，默认追求最小权限",
      "特殊服务（如 API Gateway、STS、KMS、S3）需应用专门映射规则",
      "猜测扩展权限应与原始权限分离，便于审计和回滚"
    ],
    "assumptions": [
      "CloudTrail 日志完整且事件源字段可靠",
      "source_mode: source"
    ],
    "other_constraints": [
      "跨账号/跨区域大时间窗会显著增加下载与解析成本",
      "策略推断精度受 CloudTrail 记录粒度与服务模型版本影响"
    ]
  }
]
