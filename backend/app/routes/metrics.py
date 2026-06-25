from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api", tags=["metrics"])

_PLATFORM_PATTERNS: dict[str, str] = {
    "arm64": r"\barm64\b",
    "amd64": r"\bamd64\b",
    "x86": r"\b(SSE|AVX|MMX)\b",
    "neon": r"\bNEON\b",
    "arm_asm": r"TEXT\s+·|NOSPLIT|LDAXR|STLXR",
    "arm_hw": r"cpu\.ARM64\.",
    "linux": r"\blinux\b",
    "windows": r"\bwindows\b",
    "darwin": r"\bdarwin\b",
    "goos": r"runtime\.GOOS",
    "goarch": r"runtime\.GOARCH",
    "build_tag": r"//go:build.*(arm64|amd64|linux|windows|darwin)",
    "platform_suffix": r"_[a-z]+\.(go|s)$",
    "syscall": r"\bsyscall\.[A-Za-z0-9_]+\b|\bunix\.[A-Za-z0-9_]+\b",
}

_GO_KEYWORDS = {
    "break", "default", "func", "interface", "select", "case", "defer", "go", "map", "struct",
    "chan", "else", "goto", "package", "switch", "const", "fallthrough", "if", "range", "type",
    "continue", "for", "import", "return", "var", "true", "false", "nil",
}


class CandidateRecord(BaseModel):
    code: str = ""
    compile_ok: bool | None = None
    residue: bool | None = None
    residues: list[str] = Field(default_factory=list)
    test_pass: bool | None = None
    runtime_pass: bool | None = None
    selected: bool | None = None


class SampleRecord(BaseModel):
    id: int | None = None
    migration_type: str = "arch"
    split: str = ""
    has_gt: bool = False
    target_code: str = ""
    target_os: str = "linux"
    target_arch: str = "riscv64"
    candidates: list[CandidateRecord] = Field(default_factory=list)
    selected_index: int | None = None
    selected_code: str = ""
    selected_compile_ok: bool | None = None
    selected_residue: bool | None = None
    selected_test_pass: bool | None = None
    selected_runtime_pass: bool | None = None


class MetricsRequest(BaseModel):
    samples: list[SampleRecord]
    pass_k: int = 5


def _normalize_code(code: str) -> list[str]:
    text = re.sub(r"//.*?$|/\*.*?\*/", " ", code or "", flags=re.M | re.S)
    text = re.sub(r'"(?:\\.|[^"\\])*"', " STR ", text)
    text = re.sub(r"'(?:\\.|[^'\\])*'", " CHR ", text)
    text = re.sub(r"\s+", " ", text).strip().lower()
    return re.findall(r"[a-z_][a-z0-9_]*|\d+|==|!=|<=|>=|&&|\|\||[:+\-*/%{}()[\].,]", text)


def _choose_sample_code(sample: SampleRecord) -> str:
    if sample.selected_code:
        return sample.selected_code
    if sample.selected_index is not None and 0 <= sample.selected_index < len(sample.candidates):
        return sample.candidates[sample.selected_index].code
    for candidate in sample.candidates:
        if candidate.compile_ok:
            return candidate.code
    return sample.candidates[0].code if sample.candidates else ""


def _sample_residue(sample: SampleRecord, code: str) -> bool:
    if sample.selected_residue is not None:
        return bool(sample.selected_residue)
    if sample.selected_index is not None and 0 <= sample.selected_index < len(sample.candidates):
        candidate = sample.candidates[sample.selected_index]
        if candidate.residue is not None:
            return bool(candidate.residue)
        if candidate.residues:
            return True
    for candidate in sample.candidates:
        if candidate.selected:
            if candidate.residue is not None:
                return bool(candidate.residue)
            if candidate.residues:
                return True
    return any(re.search(pattern, code or "", re.IGNORECASE) for pattern in _PLATFORM_PATTERNS.values())


def _sample_compile_ok(sample: SampleRecord) -> bool | None:
    if sample.selected_compile_ok is not None:
        return bool(sample.selected_compile_ok)
    if sample.selected_index is not None and 0 <= sample.selected_index < len(sample.candidates):
        return sample.candidates[sample.selected_index].compile_ok
    for candidate in sample.candidates:
        if candidate.selected:
            return candidate.compile_ok
    for candidate in sample.candidates:
        if candidate.compile_ok is True:
            return True
    for candidate in sample.candidates:
        if candidate.compile_ok is False:
            return False
    return None


def _sample_test_pass(sample: SampleRecord) -> bool | None:
    if sample.selected_test_pass is not None:
        return bool(sample.selected_test_pass)
    if sample.selected_runtime_pass is not None:
        return bool(sample.selected_runtime_pass)
    if sample.selected_index is not None and 0 <= sample.selected_index < len(sample.candidates):
        candidate = sample.candidates[sample.selected_index]
        if candidate.test_pass is not None:
            return bool(candidate.test_pass)
        if candidate.runtime_pass is not None:
            return bool(candidate.runtime_pass)
    for candidate in sample.candidates:
        if candidate.selected:
            if candidate.test_pass is not None:
                return bool(candidate.test_pass)
            if candidate.runtime_pass is not None:
                return bool(candidate.runtime_pass)
    return None


def _candidate_valid_for_pass(candidate: CandidateRecord) -> bool:
    if candidate.compile_ok is False:
        return False
    if candidate.test_pass is not None:
        return bool(candidate.test_pass)
    if candidate.runtime_pass is not None:
        return bool(candidate.runtime_pass)
    return bool(candidate.compile_ok)


def _pass_at_k(n: int, c: int, k: int) -> float:
    if n <= 0 or c <= 0 or k <= 0:
        return 0.0
    k = min(k, n)
    if c >= n or n - c < k:
        return 1.0
    return 1.0 - (math.comb(n - c, k) / math.comb(n, k))


def _token_ngrams(tokens: list[str], n: int) -> Counter:
    if len(tokens) < n:
        return Counter()
    return Counter(tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1))


def _bleu_like(reference: list[str], candidate: list[str]) -> float:
    if not reference or not candidate:
        return 0.0
    precisions = []
    for n in range(1, 5):
        ref_ngrams = _token_ngrams(reference, n)
        cand_ngrams = _token_ngrams(candidate, n)
        if not cand_ngrams:
            precisions.append(0.0)
            continue
        overlap = sum(min(count, ref_ngrams[gram]) for gram, count in cand_ngrams.items())
        precisions.append((overlap + 1e-9) / (sum(cand_ngrams.values()) + 1e-9))
    geo = math.exp(sum(math.log(max(p, 1e-9)) for p in precisions) / 4)
    bp = 1.0 if len(candidate) > len(reference) else math.exp(1 - (len(reference) / max(len(candidate), 1)))
    return max(0.0, min(1.0, geo * bp))


def codebleu_like(reference: str, candidate: str) -> float:
    ref_tokens = _normalize_code(reference)
    cand_tokens = _normalize_code(candidate)
    bleu = _bleu_like(ref_tokens, cand_tokens)
    ref_kw = Counter(tok for tok in ref_tokens if tok in _GO_KEYWORDS)
    cand_kw = Counter(tok for tok in cand_tokens if tok in _GO_KEYWORDS)
    kw_denom = max(sum(ref_kw.values()), sum(cand_kw.values()), 1)
    kw = sum(min(ref_kw[t], cand_kw[t]) for t in set(ref_kw) | set(cand_kw)) / kw_denom
    sig = {"func", "package", "import", "return", "if", "for", "switch", "range", "struct"}
    ref_struct = Counter(tok for tok in ref_tokens if tok in sig)
    cand_struct = Counter(tok for tok in cand_tokens if tok in sig)
    struct_denom = max(sum(ref_struct.values()), sum(cand_struct.values()), 1)
    struct = sum(min(ref_struct[t], cand_struct[t]) for t in set(ref_struct) | set(cand_struct)) / struct_denom
    return round(max(0.0, min(1.0, 0.5 * bleu + 0.25 * kw + 0.25 * struct)), 4)


def _aggregate_samples(samples: list[SampleRecord], pass_k: int, include_rows: bool = False) -> dict[str, Any]:
    prr_hits = 0
    cpbpr_hits = 0
    pass_values: list[float] = []
    codebleu_scores: list[float] = []
    bcr_hits = 0
    bcr_total = 0
    sample_rows: list[dict[str, Any]] = []

    for sample in samples:
        selected_code = _choose_sample_code(sample)
        residue = _sample_residue(sample, selected_code)
        compile_ok = _sample_compile_ok(sample)
        test_pass = _sample_test_pass(sample)

        prr_hits += 1 if residue else 0
        cpbpr_hits += 1 if compile_ok is True else 0

        n = len(sample.candidates)
        c = sum(1 for candidate in sample.candidates if _candidate_valid_for_pass(candidate))
        pass_value = _pass_at_k(n, c, pass_k) if n else 0.0
        if n:
            pass_values.append(pass_value)

        codebleu = None
        if sample.has_gt and sample.target_code.strip() and selected_code.strip():
            codebleu = codebleu_like(sample.target_code, selected_code)
            codebleu_scores.append(codebleu)

        if sample.has_gt and sample.split == "full":
            bcr_total += 1
            if test_pass is True:
                bcr_hits += 1

        if include_rows:
            sample_rows.append({
                "id": sample.id,
                "migration_type": sample.migration_type,
                "split": sample.split,
                "has_gt": sample.has_gt,
                "residue": residue,
                "compile_ok": compile_ok,
                "test_pass": test_pass,
                "selected_code": selected_code,
                "codebleu": codebleu,
                "pass_at_k_input": {"n": n, "c": c, "k": pass_k, "value": pass_value} if n else None,
            })

    total = len(samples)
    return {
        "overall": {
            "prr": round(prr_hits / total, 4) if total else 0.0,
            "cpbpr": round(cpbpr_hits / total, 4) if total else 0.0,
            "pass_at_k": round(sum(pass_values) / len(pass_values), 4) if pass_values else 0.0,
            "codebleu": round(sum(codebleu_scores) / len(codebleu_scores), 4) if codebleu_scores else None,
            "bcr": round(bcr_hits / bcr_total, 4) if bcr_total else None,
            "counts": {
                "samples": total,
                "pass_samples": len(pass_values),
                "codebleu_samples": len(codebleu_scores),
                "bcr_samples": bcr_total,
            },
        },
        "samples": sample_rows,
    }


@router.post("/metrics/evaluate")
def evaluate_metrics(req: MetricsRequest):
    if not req.samples:
        raise HTTPException(status_code=400, detail="samples cannot be empty")

    pass_k = max(1, min(int(req.pass_k), 20))
    agg = _aggregate_samples(req.samples, pass_k, include_rows=True)

    by_migration_type: dict[str, list[SampleRecord]] = {}
    for sample in req.samples:
        mt = "os" if str(sample.migration_type).lower() == "os" else "arch"
        by_migration_type.setdefault(mt, []).append(sample)

    grouped = {
        mt: _aggregate_samples(items, pass_k, include_rows=False)["overall"]
        for mt, items in by_migration_type.items()
    }

    return {
        "overall": agg["overall"],
        "grouped": grouped,
        "sample_count": len(req.samples),
        "pass_k": pass_k,
        "samples": agg["samples"],
    }
