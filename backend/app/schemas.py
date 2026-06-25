from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "archmas-backend"


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    reply: str


class RunProjectRequest(BaseModel):
    run_type: str = "knomas"  # knomas | ccgmas
    run_stage: str = "all"  # all | planning | codegen | ta
    case_dir: str | None = None
    test_loop: int = 0
    ta_project_root: str = ""
    model_profile: str = "default"
    model_name: str = ""
    model_base_url: str = ""
    model_api_key: str = ""
    prefer_cache: bool = True
    cache_version: str = "v1"

    # CCGMAS 函数级输入（替代旧 case_dir 驱动）
    source_code: str = ""
    generic_code: str = ""
    migration_type: str = "arch"
    source_platform: str = ""
    target_platform: str = ""


class RunProjectResponse(BaseModel):
    accepted: bool
    message: str
    run_id: str


class RunStatusResponse(BaseModel):
    run_id: str
    status: str
    stage: str = "queued"
    progress: int = 0
    run_type: str = "knomas"
    model_profile: str = "default"
    model_name: str = ""
    model_base_url: str = ""
    model_api_key_masked: str = ""
    return_code: int | None = None
    started_at: float
    finished_at: float | None = None
    log_file: str
    metrics: dict = {}


class ArtifactItem(BaseModel):
    artifact_id: str
    name: str
    rel_path: str
    source_rel_path: str = ""
    kind: str = ""
    scope: str = ""
    size: int
    updated_at: float


class RunArtifactsResponse(BaseModel):
    run_id: str
    base_dir: str
    outputs: list[ArtifactItem]
    logs: list[ArtifactItem]
    memory: list[ArtifactItem]


class ArtifactPreviewResponse(BaseModel):
    artifact_id: str
    name: str
    rel_path: str
    content_type: str
    preview: str
    truncated: bool
