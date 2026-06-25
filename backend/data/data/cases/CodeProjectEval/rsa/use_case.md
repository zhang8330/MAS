[
  {
    "use_case_name": "使用 rsa 库进行密钥生成、加解密与签名验签",
    "primary_actor": "应用开发者/安全工程师",
    "secondary_actor": [
      "操作系统随机源",
      "文件系统（PEM/DER 密钥存储）",
      "命令行调用方"
    ],
    "trigger": "调用方执行 rsa.newkeys()/encrypt()/decrypt()/sign()/verify() 或 CLI 子命令",
    "use_case_description": "rsa 提供纯 Python 的 RSA 密钥管理与 PKCS#1 v1.5 加解密签名能力，并支持 PEM/DER 互转、OpenSSL 公钥格式与并行素数生成。",
    "preconditions": [
      "输入数据与密钥格式有效（PEM 或 DER）",
      "待加密消息长度满足密钥位数与填充约束",
      "随机数源可用以支持密钥生成与填充"
    ],
    "postconditions": [
      "生成可持久化的 RSA 公私钥对",
      "成功返回密文、明文或签名结果",
      "验签结果明确（通过或抛出 VerificationError）"
    ],
    "main_flow": [
      "1. 通过 newkeys 或 keygen 生成 RSA 密钥对",
      "2. 根据业务选择公钥加密/私钥解密或私钥签名/公钥验签",
      "3. pkcs1 模块对输入执行 PKCS#1 v1.5 填充与核心运算",
      "4. core 模块完成整数级模幂运算，必要时使用 CRT 加速",
      "5. 返回处理结果并可将密钥导出为 PEM/DER"
    ],
    "alternative_flows": [
      "A1：使用 parallel.getprime 启用并行素数生成提升大密钥生成速度。",
      "A2：通过 util.private_to_public 从私钥提取公钥。",
      "A3：通过 cli Encrypt/Decrypt/Sign/VerifyOperation 在命令行批处理文件。"
    ],
    "exception_flows": [
      "E1：消息过长或填充格式错误引发 OverflowError/DecryptionError。",
      "E2：签名不匹配引发 VerificationError。",
      "E3：模逆不存在引发 NotRelativePrimeError（密钥参数不满足互素约束）。",
      "E4：密钥格式非法引发 ValueError 或解析异常。"
    ],
    "priority": "High",
    "business_rules": [
      "密钥参数必须满足 RSA 数学条件（n=p*q，e 与 φ(n) 互素）",
      "签名与验签必须使用一致的哈希方法标识",
      "私钥相关运算优先启用盲化/CRT 以提升安全与性能"
    ],
    "assumptions": [
      "调用方理解 PKCS#1 v1.5 的适用边界与安全建议",
      "source_mode: source"
    ],
    "other_constraints": [
      "纯 Python 实现性能受限于大整数运算开销",
      "多进程并行生成素数会额外占用系统资源"
    ]
  }
]
