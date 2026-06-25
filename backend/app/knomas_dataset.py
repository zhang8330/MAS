from pathlib import Path
import shutil

from .config import get_settings

KEY_ARTIFACTS = [
    "class_diagram.md",
    "component_diagram.md",
    "package_diagram.md",
    "use_case.md",
    "entity_relationship_diagram.md",
    "tech_stack.json",
    "input_source.md",
    "isoftdev_generation_report.md",
]


def _resolve_knomas_data_root() -> Path:
    settings = get_settings()
    p = Path(settings.knomas_data_root)
    if not p.is_absolute():
        p = Path(__file__).resolve().parents[1] / p
    return p


def _cases_root() -> Path:
    return _resolve_knomas_data_root() / "cases"


def _case_dir(dataset: str, case_name: str) -> Path:
    direct_case = _cases_root() / dataset
    if case_name == dataset:
        return direct_case
    return _cases_root() / dataset / case_name


def _has_key_artifacts(path: Path) -> bool:
    return path.is_dir() and any((path / name).is_file() for name in KEY_ARTIFACTS)


def _case_dir_for_runtime(path: Path) -> str:
    try:
        rel = path.relative_to(_resolve_knomas_data_root().parent)
        return str(rel).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _build_case_item(dataset: str, case_name: str, path: Path) -> dict:
    files = sorted([x.name for x in path.glob("*") if x.is_file()])
    key_artifacts = [f for f in files if f in KEY_ARTIFACTS]
    return {
        "name": case_name,
        "case_name": case_name,
        "dataset": dataset,
        "path": str(path).replace("\\", "/"),
        "case_dir": _case_dir_for_runtime(path),
        "file_count": len(files),
        "key_artifacts": key_artifacts,
        "artifacts_presence": {k: (k in key_artifacts) for k in sorted(KEY_ARTIFACTS)},
    }


def list_knomas_datasets() -> list[str]:
    cases_root = _cases_root()
    if not cases_root.exists() or not cases_root.is_dir():
        return []
    return sorted([p.name for p in cases_root.iterdir() if p.is_dir()])


def knomas_dataset_exists(dataset: str) -> bool:
    return dataset in set(list_knomas_datasets())


def list_knomas_cases(limit: int = 1000, dataset: str | None = None, keyword: str | None = None) -> list[dict]:
    cases_root = _cases_root()
    if not cases_root.exists():
        return []

    available_datasets = list_knomas_datasets()
    datasets_to_scan = [dataset] if dataset in available_datasets else available_datasets
    keyword_l = (keyword or "").strip().lower()

    items = []
    for ds in datasets_to_scan:
        ds_root = cases_root / ds
        if not ds_root.exists() or not ds_root.is_dir():
            continue

        if _has_key_artifacts(ds_root):
            item = _build_case_item(ds, ds, ds_root)
            if not keyword_l or keyword_l in item["name"].lower() or keyword_l in item["path"].lower():
                items.append(item)
                if len(items) >= limit:
                    return items
            continue

        for p in sorted(ds_root.iterdir()):
            if not p.is_dir():
                continue
            if not _has_key_artifacts(p):
                continue
            item = _build_case_item(ds, p.name, p)
            if keyword_l and keyword_l not in item["name"].lower() and keyword_l not in item["path"].lower():
                continue
            items.append(item)
            if len(items) >= limit:
                return items
    return items


def get_knomas_root_info() -> dict:
    root = _resolve_knomas_data_root()
    cases_root = root / "cases"
    return {
        "data_root": str(root).replace('\\', '/'),
        "cases_root": str(cases_root).replace('\\', '/'),
        "exists": root.exists(),
        "cases_exists": cases_root.exists(),
        "datasets": list_knomas_datasets(),
    }


def get_knomas_case_detail(dataset: str, case_name: str) -> dict | None:
    d = _case_dir(dataset, case_name)
    if not d.exists() or not d.is_dir():
        return None

    files = {}
    for k in KEY_ARTIFACTS:
        p = d / k
        if p.exists() and p.is_file():
            files[k] = p.read_text(encoding="utf-8", errors="replace")
        else:
            files[k] = ""

    return {
        "dataset": dataset,
        "case_name": case_name,
        "path": str(d).replace('\\', '/'),
        "files": files,
    }


def create_knomas_case(dataset: str, case_name: str, files: dict | None = None) -> dict:
    d = _case_dir(dataset, case_name)
    d.mkdir(parents=True, exist_ok=False)
    payload = files or {}

    for k in KEY_ARTIFACTS:
        p = d / k
        default = "{}" if k.endswith(".json") else ""
        p.write_text(str(payload.get(k, default)), encoding="utf-8")

    return {
        "ok": True,
        "dataset": dataset,
        "case_name": case_name,
        "path": str(d).replace('\\', '/'),
        "case_dir": _case_dir_for_runtime(d),
    }


def update_knomas_case(dataset: str, case_name: str, files: dict) -> dict:
    d = _case_dir(dataset, case_name)
    if not d.exists() or not d.is_dir():
        return {"ok": False}

    for k, v in (files or {}).items():
        if k not in KEY_ARTIFACTS:
            continue
        (d / k).write_text(str(v or ""), encoding="utf-8")

    return {
        "ok": True,
        "dataset": dataset,
        "case_name": case_name,
        "path": str(d).replace('\\', '/'),
        "case_dir": _case_dir_for_runtime(d),
    }


def delete_knomas_case(dataset: str, case_name: str) -> dict:
    d = _case_dir(dataset, case_name)
    if not d.exists() or not d.is_dir():
        return {"ok": False}
    shutil.rmtree(d)
    return {"ok": True}
