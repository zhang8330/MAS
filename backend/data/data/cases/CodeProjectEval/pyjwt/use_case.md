[
  {
    "use_case_name": "使用 PyJWT 进行 JWT 编码、校验与密钥发现",
    "primary_actor": "后端开发者/API 网关服务",
    "secondary_actor": [
      "身份提供方（IdP/OAuth2/OIDC）",
      "JWK/JWKS 密钥服务端点",
      "可选 cryptography 库"
    ],
    "trigger": "调用方执行 jwt.encode()/decode() 或 PyJWKClient.get_signing_key_from_jwt()",
    "use_case_description": "提供 JWT/JWS 的签名与验签、标准声明校验、JWK/JWKS 密钥解析与缓存，支持 HMAC、RSA、EC、EdDSA 等算法。",
    "preconditions": [
      "token、密钥与算法配置一致且格式合法",
      "若使用 RSA/EC/EdDSA 等算法，运行环境已安装 cryptography",
      "若使用 JWKS 客户端，远程 URI 可访问"
    ],
    "postconditions": [
      "编码成功返回紧凑 JWT 字符串",
      "解码成功返回 payload（或 complete 结构）",
      "验证失败抛出明确异常（签名、过期、受众、发行方等）"
    ],
    "main_flow": [
      "1. 调用方准备 payload 与签名密钥，指定算法（如 HS256/RS256）",
      "2. PyJWT/PyJWS 根据算法对象完成签名并生成 token",
      "3. 验证侧解析 token 头部与 payload，准备公钥或共享密钥",
      "4. 执行签名校验并按配置验证 exp/nbf/iat/aud/iss/sub/jti",
      "5. 验证通过则返回 claims，业务继续执行"
    ],
    "alternative_flows": [
      "A1：通过 PyJWKClient 从 JWKS 端点自动获取并缓存 kid 对应签名公钥。",
      "A2：使用 decode_complete 同时拿到 header/payload/signature 便于审计。",
      "A3：注册自定义算法（register_algorithm）扩展签名能力。"
    ],
    "exception_flows": [
      "E1：签名不匹配抛出 InvalidSignatureError。",
      "E2：token 过期抛出 ExpiredSignatureError。",
      "E3：aud/iss/sub/jti 校验失败抛出对应 Invalid*Error。",
      "E4：算法依赖缺失（如 cryptography）抛出 MissingCryptographyError。",
      "E5：JWKS 拉取失败抛出 PyJWKClientConnectionError。"
    ],
    "priority": "High",
    "business_rules": [
      "验签时必须显式限制允许算法集合，避免算法降级风险",
      "标准声明校验策略由 options 与运行参数共同决定",
      "远程密钥获取应使用缓存并支持刷新重试"
    ],
    "assumptions": [
      "系统时钟可信且与签发方误差在可接受 leeway 范围内",
      "source_mode: source"
    ],
    "other_constraints": [
      "高并发下 JWKS 刷新频率需平衡实时性与网络开销",
      "不同 IdP 的 kid/alg 策略差异可能影响互操作"
    ]
  }
]
