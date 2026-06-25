[
  {
    "use_case_name": "基于 Simple JWT 完成登录鉴权与令牌生命周期管理",
    "primary_actor": "前后端开发者/API 客户端",
    "secondary_actor": [
      "Django REST Framework",
      "Django 用户模型与数据库",
      "JWT 签名与校验后端（TokenBackend）",
      "可选黑名单子应用 token_blacklist"
    ],
    "trigger": "客户端调用 TokenObtain/Refresh/Verify/Blacklist 等 API 端点或受保护接口",
    "use_case_description": "在 Django REST Framework 中提供 JWT 登录签发、请求鉴权、刷新校验与撤销能力，支持有状态与无状态用户模式。",
    "preconditions": [
      "Django 与 DRF 已正确安装并完成基础配置",
      "SIMPLE_JWT 配置项（算法、签名密钥、过期时间等）有效",
      "若启用黑名单能力，token_blacklist app 已迁移并可用"
    ],
    "postconditions": [
      "合法用户可获得 access/refresh 或 sliding token",
      "受保护接口可通过 Authorization 头完成身份认证",
      "被撤销或过期的 token 将被拒绝访问"
    ],
    "main_flow": [
      "1. 客户端提交凭据到 TokenObtainPairView/TokenObtainSlidingView",
      "2. Serializer 验证凭据并创建 Token（含 exp/iat/jti 等 claim）",
      "3. 客户端携带 access token 访问业务接口，JWTAuthentication 提取并校验 token",
      "4. 认证层解析用户（数据库用户或 TokenUser）并将 user/token 注入请求上下文",
      "5. access 过期后，客户端调用 TokenRefreshView 或 TokenRefreshSlidingView 获取新 token",
      "6. 如需主动失效，客户端调用 TokenBlacklistView 将 refresh/sliding token 加入黑名单",
      "7. 后续验证流程拒绝黑名单或无效 token"
    ],
    "alternative_flows": [
      "A1：启用无状态认证（JWTStatelessUserAuthentication），直接返回 TokenUser，无需数据库查用户。",
      "A2：启用 rotate refresh token，刷新时同时返回新的 refresh token。",
      "A3：仅调用 TokenVerifyView 校验 token 有效性，不执行业务访问。"
    ],
    "exception_flows": [
      "E1：凭据错误或用户不可用时抛出 AuthenticationFailed。",
      "E2：token 结构错误、签名错误或类型不匹配时抛出 InvalidToken/TokenError。",
      "E3：token 过期时抛出 ExpiredTokenError 或 TokenBackendExpiredToken。",
      "E4：启用黑名单后 token 已撤销时校验失败并返回认证错误。"
    ],
    "priority": "High",
    "business_rules": [
      "所有受保护接口默认通过 Bearer Token 头进行认证",
      "token 过期、撤销与签名校验必须严格执行",
      "用户状态校验规则受 CHECK_USER_IS_ACTIVE 等配置控制"
    ],
    "assumptions": [
      "客户端能正确保存与轮换 token",
      "服务端时钟与时区设置一致可控",
      "source_mode: source"
    ],
    "other_constraints": [
      "密钥管理策略需满足生产安全要求",
      "黑名单模式会引入额外数据库读写开销"
    ]
  }
]
