[
  {
    "use_case_name": "解析、构建并传输 HL7 v2.x 消息",
    "primary_actor": "医疗集成开发者/接口服务",
    "secondary_actor": [
      "医院 HIS/LIS/EMR 系统",
      "TCP/MLLP 通道",
      "上游或下游 HL7 消息网关"
    ],
    "trigger": "调用方执行 hl7.parse_hl7()、Message 字段访问赋值、MLLPClient/异步 HL7Stream 收发",
    "use_case_description": "python-hl7 提供 HL7 文本到结构化容器的解析、字段级读写、ACK 构建以及同步/异步 MLLP 传输能力，用于医疗系统间消息互通。",
    "preconditions": [
      "输入数据满足 HL7 基本段结构（如以 MSH 开头）",
      "约定的分隔符、字符编码与对端系统兼容",
      "若走网络传输，目标 MLLP 服务可达"
    ],
    "postconditions": [
      "HL7 文本被解析为 Message/Batch/File 容器结构",
      "业务可按段-字段-重复-组件-子组件路径读写数据",
      "可选生成 ACK 或经 MLLP 通道发送并接收响应"
    ],
    "main_flow": [
      "1. 接收 HL7 原始文本或字节流",
      "2. parse_hl7 自动识别并解析为 Message/Batch/File",
      "3. 通过 Accessor 或下标路径提取/修改关键字段",
      "4. 必要时进行 escape/unescape 与时间字段转换",
      "5. 构建 ACK（create_ack）或序列化为 HL7 字符串",
      "6. 通过 MLLPClient 或 mllp.streams 发送并处理响应"
    ],
    "alternative_flows": [
      "A1：处理批量/文件协议，解析 BHS/BTS 或 FHS/FTS 包裹消息。",
      "A2：使用异步 HL7StreamReader/Writer 在 asyncio 服务中读写 MLLP 块。",
      "A3：使用 util.split_file 将混合 HL7 文件拆分成单条消息。"
    ],
    "exception_flows": [
      "E1：段结构不合法触发 MalformedSegmentException。",
      "E2：批处理或文件包裹结构不完整触发 MalformedBatchException/MalformedFileException。",
      "E3：MLLP 分帧错误触发 InvalidBlockError 或 MLLPException。",
      "E4：日期时间字段格式错误触发 ValueError（parse_datetime）。"
    ],
    "priority": "High",
    "business_rules": [
      "索引遵循 HL7 规范语义（从 1 开始）",
      "MSH/BHS/FHS 首段分隔符处理需遵循 HL7 特殊规则",
      "序列化消息应以段分隔符结尾以保持标准兼容"
    ],
    "assumptions": [
      "上下游系统遵循 HL7 v2.x 与 MLLP 约定",
      "source_mode: source"
    ],
    "other_constraints": [
      "不同医院对可选字段和编码约定可能不一致",
      "高吞吐场景下需关注解析与网络 I/O 性能"
    ]
  }
]
