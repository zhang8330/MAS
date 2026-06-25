[
  {
    "use_case_name": "生成混合图像（Hybrid Image）",
    "primary_actor": "开发者或命令行用户",
    "secondary_actor": [
      "NumPy/OpenCV 运行环境"
    ],
    "trigger": "调用 create_hybrid_image(img1, img2, ...) 并提供滤波参数",
    "use_case_description": "系统分别对两张输入图像执行低通或高通滤波，再按 mixin_ratio 进行加权融合并输出 uint8 混合图像。",
    "preconditions": [
      "img1 与 img2 维度兼容",
      "卷积核尺寸为奇数",
      "依赖库 cv2 与 numpy 可用"
    ],
    "postconditions": [
      "返回同尺寸的混合图像数组",
      "输出像素范围被裁剪到 [0,255]",
      "输出类型为 uint8"
    ],
    "main_flow": [
      "1. 输入两张图像和两组滤波参数",
      "2. 按 high_low1 对 img1 执行 low_pass 或 high_pass",
      "3. 按 high_low2 对 img2 执行 low_pass 或 high_pass",
      "4. 根据 mixin_ratio 加权融合两张处理后图像",
      "5. 进行缩放、裁剪并返回结果"
    ],
    "alternative_flows": [
      "A1：输入图像为 uint8 时先归一化到 [0,1] 再参与滤波。"
    ],
    "exception_flows": [
      "E1：图像维度不匹配时，底层数组运算抛出异常。",
      "E2：非法 kernel 参数导致卷积计算失败。"
    ],
    "priority": "High",
    "business_rules": [
      "high_pass(img)=img-low_pass(img)",
      "mixin_ratio 控制两路图像贡献比例",
      "Gaussian kernel 需归一化"
    ],
    "assumptions": [
      "输入图像已对齐（同尺寸/同通道）",
      "调用方负责参数合法性"
    ],
    "other_constraints": [
      "实现语言为 Python",
      "核心函数需通过 unit_test 与 acceptance_test"
    ]
  }
]
