Param(
  [string]$BaseUrl = "http://localhost:8000",
  [string]$SourceCode = "package main`n`nfunc add(a int, b int) int { return a + b }",
  [string]$GenericCode = "",
  [string]$Model = "gpt-4o-mini",
  [string]$Provider = "openai",
  [string]$ApiBase = "https://api.openai.com/v1",
  [string]$ApiKey = "",
  [int]$K = 3,
  [int]$RgaMaxIter = 2,
  [switch]$SkipScenarioB
)

$ErrorActionPreference = "Stop"

function Write-Section($title) {
  Write-Host ""
  Write-Host "==================== $title ====================" -ForegroundColor Cyan
}

function Invoke-PostJson {
  Param(
    [string]$Url,
    [hashtable]$Body,
    [int]$TimeoutSec = 600
  )
  $json = $Body | ConvertTo-Json -Depth 20
  return Invoke-RestMethod -Method Post -Uri $Url -ContentType "application/json; charset=utf-8" -Body $json -TimeoutSec $TimeoutSec
}

function Build-RuntimeConfig([bool]$WithKey) {
  if ($WithKey -and -not [string]::IsNullOrWhiteSpace($ApiKey)) {
    return @{
      provider = $Provider
      base_url = $ApiBase
      api_key = $ApiKey
      model = $Model
    }
  }
  return @{
    provider = $Provider
    base_url = $ApiBase
    api_key = ""
    model = $Model
  }
}

function Build-EvalProfiles([bool]$WithKey) {
  $p = Build-RuntimeConfig -WithKey:$WithKey
  return @($p, $p, $p)
}

function Show-CheckResult($name, $ok, $detail) {
  if ($ok) {
    Write-Host "[PASS] $name - $detail" -ForegroundColor Green
  } else {
    Write-Host "[FAIL] $name - $detail" -ForegroundColor Red
  }
}

function Get-FriendlyError([System.Management.Automation.ErrorRecord]$err) {
  $raw = $err.Exception.Message
  try {
    $resp = $err.ErrorDetails.Message
    if ($resp) { return $resp }
  } catch {}
  return $raw
}

# ============== Scenario A: With Key ==============
Write-Section "Scenario A (有 key): 一键执行 /api/generate"
if ([string]::IsNullOrWhiteSpace($ApiKey)) {
  Write-Host "未提供 -ApiKey，跳过场景 A（可传 -ApiKey 后重试）" -ForegroundColor Yellow
} else {
  $bodyA = @{
    source_code = $SourceCode
    generic_code = $GenericCode
    migration_type = "arch"
    source_platform = "amd64"
    target_platform = "riscv64"
    model = $Model
    k = $K
    rga_max_iter = $RgaMaxIter
    runtime_llm_config = Build-RuntimeConfig -WithKey:$true
    eval_profiles = Build-EvalProfiles -WithKey:$true
    enable_test_validation = $true
  }

  try {
    $resA = Invoke-PostJson -Url "$BaseUrl/api/generate" -Body $bodyA -TimeoutSec 600

    $hasCore = $null -ne $resA.arp -and $null -ne $resA.srs -and $null -ne $resA.semantic_info -and $null -ne $resA.rga_quality -and $null -ne $resA.candidates -and $null -ne $resA.va
    Show-CheckResult "A1 契约字段完整" $hasCore "arp/srs/semantic_info/rga_quality/candidates/va"

    $compileOk = $resA.va.n_compile_ok
    $total = $resA.va.total
    $residue = $resA.va.residue_rate
    $testPass = $resA.va.test_validation.test_pass_rate
    Write-Host "A 指标: Compile@k=$compileOk/$total, residue_rate=$residue, test_pass_rate=$testPass"

    Show-CheckResult "A2 非无key降级" $true "未触发鉴权缺失错误"
  }
  catch {
    $errMsg = Get-FriendlyError $_
    Show-CheckResult "A1/A2" $false $errMsg
  }
}

# ============== Scenario B: No Key ==============
if (-not $SkipScenarioB) {
  Write-Section "Scenario B (无 key): 返回清晰提示"
  $bodyB = @{
    source_code = $SourceCode
    generic_code = $GenericCode
    migration_type = "arch"
    source_platform = "amd64"
    target_platform = "riscv64"
    model = $Model
    k = 1
    rga_max_iter = 1
    runtime_llm_config = Build-RuntimeConfig -WithKey:$false
    eval_profiles = Build-EvalProfiles -WithKey:$false
    enable_test_validation = $false
  }

  try {
    $null = Invoke-PostJson -Url "$BaseUrl/api/generate" -Body $bodyB -TimeoutSec 120
    Show-CheckResult "B1 无 key 场景" $false "请求意外成功，请确认后端是否允许匿名或默认key"
  }
  catch {
    $errText = Get-FriendlyError $_
    $lower = $errText.ToLower()
    $isClear = $lower.Contains("api key") -or $lower.Contains("unauthorized") -or $lower.Contains("authentication") -or $lower.Contains("invalid_api_key") -or $lower.Contains("401")
    Show-CheckResult "B1 返回清晰提示" $isClear $errText
    if (-not $isClear) {
      Write-Host "建议前端展示友好文案：未检测到可用模型密钥（API Key）..." -ForegroundColor Yellow
    }
  }
}

# ============== Scenario C: Step-by-step ==============
Write-Section "Scenario C (分步执行): /api/run/paa→rga→cga→va"
$runtimeWithKey = Build-RuntimeConfig -WithKey:([bool](-not [string]::IsNullOrWhiteSpace($ApiKey)))
$evalWithKey = Build-EvalProfiles -WithKey:([bool](-not [string]::IsNullOrWhiteSpace($ApiKey)))

$common = @{
  source_code = $SourceCode
  generic_code = $GenericCode
  migration_type = "arch"
  source_platform = "amd64"
  target_platform = "riscv64"
  model = $Model
  k = $K
  rga_max_iter = $RgaMaxIter
  runtime_llm_config = $runtimeWithKey
  eval_profiles = $evalWithKey
}

try {
  $paa = Invoke-PostJson -Url "$BaseUrl/api/run/paa" -Body $common -TimeoutSec 180
  $okPaa = $null -ne $paa.arp
  Show-CheckResult "C1 PAA" $okPaa "arp returned"

  $bodyRga = @{} + $common
  $bodyRga.arp = $paa.arp
  $rga = Invoke-PostJson -Url "$BaseUrl/api/run/rga" -Body $bodyRga -TimeoutSec 300
  $okRga = $null -ne $rga.srs -and $null -ne $rga.semantic_info -and $null -ne $rga.rga_quality
  Show-CheckResult "C2 RGA" $okRga "srs/semantic_info/rga_quality returned"

  $bodyCga = @{} + $common
  $bodyCga.arp = $paa.arp
  $bodyCga.srs = $rga.srs
  $cga = Invoke-PostJson -Url "$BaseUrl/api/run/cga" -Body $bodyCga -TimeoutSec 300
  $okCga = $null -ne $cga.candidates -and $cga.candidates.Count -gt 0
  Show-CheckResult "C3 CGA" $okCga "candidates count=$($cga.candidates.Count)"

  $bodyVa = @{} + $common
  $bodyVa.srs = $rga.srs
  $bodyVa.semantic_info = $rga.semantic_info
  $bodyVa.candidates = $cga.candidates
  $bodyVa.enable_test_validation = $true
  $va = Invoke-PostJson -Url "$BaseUrl/api/run/va" -Body $bodyVa -TimeoutSec 300
  $okVa = $null -ne $va.va
  Show-CheckResult "C4 VA" $okVa "va returned"

  if ($okVa) {
    Write-Host "C 指标: Compile@k=$($va.va.n_compile_ok)/$($va.va.total), residue_rate=$($va.va.residue_rate), test_pass_rate=$($va.va.test_validation.test_pass_rate)"
  }
}
catch {
  $errText = Get-FriendlyError $_
  Show-CheckResult "C 分步联调" $false $errText
}

Write-Section "验收总结"
Write-Host "已覆盖：场景A(有key)、场景B(无key)、场景C(分步执行)" -ForegroundColor Cyan
Write-Host "若你要做回归，可把本脚本加入 CI 的手工触发任务。" -ForegroundColor Cyan
