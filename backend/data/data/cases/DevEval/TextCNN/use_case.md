[
  {
    "use_case_name": "训练与测试 TextCNN 文本分类模型",
    "primary_actor": "开发者/研究人员",
    "secondary_actor": [
      "文件系统",
      "PyTorch 运行环境"
    ],
    "trigger": "用户通过 main.py 提供训练或测试参数",
    "use_case_description": "系统加载数据集并构建 TextCNN 模型，执行训练过程并保存最佳 checkpoint，随后可执行测试评估模型效果。",
    "preconditions": [
      "训练/测试数据路径存在",
      "参数可被 get_args 正确解析",
      "运行环境已安装深度学习依赖"
    ],
    "postconditions": [
      "训练阶段生成最佳模型 checkpoint",
      "测试阶段输出评估结果",
      "核心行为通过 unit_tests 与 acceptance_tests"
    ],
    "main_flow": [
      "1. 用户运行 main.py 并传入参数",
      "2. 系统解析参数并选择 train 或 test 流程",
      "3. train.py 调用 data.py 构建数据与词表",
      "4. train.py 构建 modeling.py 中 TextCNN 并训练",
      "5. 保存最佳 checkpoint",
      "6. test.py 加载模型并执行评估"
    ],
    "alternative_flows": [
      "A1：仅执行测试流程，直接读取已有 checkpoint。"
    ],
    "exception_flows": [
      "E1：参数非法导致 get_args 报错退出。",
      "E2：checkpoint 路径不存在导致测试失败。",
      "E3：训练过程数值异常导致提前终止。"
    ],
    "priority": "High",
    "business_rules": [
      "随机种子需可控以保证可复现",
      "输出张量形状需满足测试断言",
      "最佳模型保存逻辑需满足 test_save_best_checkpoints"
    ],
    "assumptions": [
      "输入文本与标签格式符合 data.py 读取要求",
      "GPU/CPU 资源满足当前 batch 规模"
    ],
    "other_constraints": [
      "实现语言为 Python",
      "模型结构为 TextCNN"
    ]
  }
]
