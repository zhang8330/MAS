[
  {
    "use_case_name": "使用 SimPy 构建离散事件仿真模型",
    "primary_actor": "仿真建模开发者/研究人员",
    "secondary_actor": [
      "业务过程生成器（process generator）",
      "资源对象（Resource/Store/Container）",
      "可选实时时钟（RealtimeEnvironment）"
    ],
    "trigger": "调用方创建 Environment 并注册 process/resource/event 后执行 run()",
    "use_case_description": "在统一事件调度器上模拟系统行为，通过事件、进程和资源队列推进仿真时间，评估吞吐、等待、拥塞与策略效果。",
    "preconditions": [
      "仿真逻辑已建模为 yield event 的生成器函数",
      "资源容量、初始状态和时间单位定义清晰",
      "若使用实时环境，运行机器时钟与性能满足约束"
    ],
    "postconditions": [
      "仿真按 until 条件结束或调度队列耗尽",
      "事件结果与资源状态可用于统计分析",
      "异常场景抛出明确错误（如 EmptySchedule、中断、实时超时）"
    ],
    "main_flow": [
      "1. 创建 Environment（或 RealtimeEnvironment）",
      "2. 注册多个 process，并在进程中 yield timeout/request/get/put 等事件",
      "3. 调用 run(until=...) 启动调度循环",
      "4. 环境按时间与优先级处理事件，唤醒相应进程继续执行",
      "5. 资源子系统按队列策略授予或释放容量（Resource/Store/Container）",
      "6. 达到终止条件后返回结果并统计关键指标"
    ],
    "alternative_flows": [
      "A1：使用 AnyOf/AllOf 组合条件事件表达并发等待逻辑。",
      "A2：使用 PriorityResource/PreemptiveResource 模拟优先级抢占。",
      "A3：使用 util.start_delayed 延后启动流程，或 subscribe_at 监听事件完成。",
      "A4：使用 RealtimeEnvironment 让仿真时间与墙钟时间同步。"
    ],
    "exception_flows": [
      "E1：调度队列为空且继续 step/run 时触发 EmptySchedule。",
      "E2：进程被 interrupt 时抛出 Interrupt 并由业务逻辑处理。",
      "E3：RealtimeEnvironment 严格模式下处理超时触发 RuntimeError。",
      "E4：资源参数非法（如负容量、非法请求量）引发 ValueError。"
    ],
    "priority": "High",
    "business_rules": [
      "仿真时钟单调递增，事件按时间与优先级稳定出队",
      "进程协作必须通过事件对象完成，不允许直接阻塞调度器",
      "资源授予遵循其队列策略（FIFO/优先级/过滤/抢占）"
    ],
    "assumptions": [
      "模型离散化程度足以表达目标系统行为",
      "source_mode: source"
    ],
    "other_constraints": [
      "复杂模型在高事件密度下会产生显著 CPU/内存开销",
      "实时仿真精度受宿主机调度延迟影响"
    ]
  }
]
