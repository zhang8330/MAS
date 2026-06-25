# MAS (Merged ArchMAS + Pro-MAS)

这是一个统一的可演示系统工程，位于 `D:/projects/MAS`。

- `backend/`：FastAPI 后端（统一 API、任务编排、日志与产物）
- `frontend/`：Vue3 + Vite 前端（数据集管理 + KnoMAS/CCGMAS 运行页）

---

## 1. 目录结构

- `backend/app/`：API、schema、数据集适配、服务逻辑
- `backend/runs/`：运行日志与产物归档
- `backend/.env.example`：后端配置模板
- `frontend/src/views/`：前端页面
- `frontend/.env.example`：前端配置模板

---

## 2. 一键启动（Windows / PowerShell）

> 目标：启动后端 + 前端，直接打开页面演示。

### 步骤 1：启动后端

```powershell
cd D:/projects/MAS/backend

# 1) 创建并激活虚拟环境（首次）
python -m venv .venv
.\.venv\Scripts\activate

# 2) 安装依赖
pip install -r requirements.txt

# 3) 准备配置（首次）
Copy-Item .env.example .env

# 4) 启动后端
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 步骤 2：启动前端（新开一个 PowerShell 窗口）

```powershell
cd D:/projects/MAS/frontend

# 1) 安装依赖
npm install

# 2) 准备配置（首次）
Copy-Item .env.example .env

# 3) 启动前端
npm run dev
```

### 步骤 3：访问

- 前端：`http://localhost:5173`
- 后端接口文档：`http://localhost:8000/docs`

---

## 3. 配置说明（可复现关键）

### 后端 `.env`（`backend/.env`）

关键字段：

- `CCG_DATASET_DB_PATH`：CCGMAS SQLite 数据库路径（例如 `D:/projects/MAS/backend/dataset.db`）
- `KNOMAS_DATA_ROOT`：KnoMAS 数据根目录（例如 `D:/projects/MAS/backend/data/data`）
- `OPENAI_API_KEY` / `OPENAI_BASE_URL`：模型访问配置

示例（PowerShell 临时覆盖）：

```powershell
$env:OPENAI_API_KEY = "your_key"
$env:OPENAI_BASE_URL = "https://api.openai.com/v1"
$env:CCG_DATASET_DB_PATH = "D:/projects/MAS/backend/dataset.db"
$env:KNOMAS_DATA_ROOT = "D:/projects/MAS/backend/data/data"
```

### 前端 `.env`（`frontend/.env`）

- `VITE_API_BASE_URL`：后端地址（默认 `http://localhost:8000`）

---

## 4. 数据来源说明（迁移来源）

- **CCGMAS 数据集**：来自 SQLite 数据库（`CCG_DATASET_DB_PATH` 指向的 DB），通过 `/api/datasets/ccg/*` 接口读取、筛选、分页。
- **KnoMAS 数据集**：来自目录树（`KNOMAS_DATA_ROOT/cases`），目录契约为：
  - `data/cases/DevEval/<case>/...`
  - `data/cases/CodeProjectEval/<case>/...`

KnoMAS 关键工件命名：

- `class_diagram.md`
- `component_diagram.md`
- `package_diagram.md`
- `use_case.md`
- `entity_relationship_diagram.md`
- `tech_stack.json`

---

## 5. 接口清单（当前）

### 数据集接口

- `GET /api/datasets/ccg/tables`：调试用，返回可见表名。
- `GET /api/datasets/ccg/stats?migration_type=arch|os`：返回 CCGMAS 统计。
- `GET /api/datasets/ccg/repos`：返回仓库及样本数量。
- `GET /api/datasets/ccg/functions?page=&page_size=&migration_type=&repo=&complexity=`：返回函数样本分页列表。
- `GET /api/datasets/knomas/info`：返回 KnoMAS 数据根目录信息。
- `GET /api/datasets/knomas/cases?dataset=DevEval|CodeProjectEval&keyword=&limit=`：返回案例列表与工件存在性。

### 运行接口

- `POST /api/project/run`：发起任务（`run_type=knomas|ccgmas`）。
- `GET /api/project/runs/{run_id}/status`：轮询状态、阶段、指标。
- `GET /api/project/runs/{run_id}/logs/stream`：SSE 实时日志。
- `GET /api/project/runs/{run_id}/artifacts`：列出产物。
- `GET /api/project/runs/{run_id}/artifacts/{artifact_id}/preview`：文本产物预览。
- `GET /api/project/runs/{run_id}/artifacts/{artifact_id}/download`：下载产物。

### 错误结构

- 参数错误或数据层异常返回统一结构：`{ code, message, detail }`（通过 HTTP `detail` 返回）。

---

## 6. 演示路径（交付验证）

1. 打开 `/datasets`，确认页面无报错。
2. 切到 **KnoMAS 数据集** Tab，选择 `DevEval`/`CodeProjectEval`，点击“去生成”。
3. 跳转 `/run?case_dir=...` 后确认 `case_dir` 自动带入，点击“开始生成”。
4. 查看运行状态、日志滚动、产物预览/下载。
5. 回到 `/datasets`，切到 **CCGMAS 数据集（数据库）** Tab，筛选并点击“去迁移”。
6. 跳转 `/ccgmas?case_dir=...` 后确认 `case_dir` 自动带入，点击“开始迁移”。
7. 查看 PAA/RGA/CGA/VA 阶段、指标、日志与产物下载。

---

## 7. 常见问题

- 前端打不开数据：先确认后端是否启动、`VITE_API_BASE_URL` 是否正确。
- KnoMAS 案例为空：检查 `KNOMAS_DATA_ROOT` 是否指向包含 `cases/DevEval` 与 `cases/CodeProjectEval` 的目录。
- CCGMAS 列表为空：检查 `CCG_DATASET_DB_PATH` 指向的数据库文件是否存在且有数据表。
