#!/usr/bin/env python3
"""Portable, privacy-safe telemetry emitter for PARA Knowledge Base operations."""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import json
import os
import re
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows fallback
    fcntl = None


SCHEMA = "para-kb.telemetry"
SCHEMA_VERSION = 1
CONFIG_RELATIVE_PATH = Path(".para-kb/config.json")
STATE_RELATIVE_PATH = Path(".para-kb/runtime/operations.json")
LOCK_RELATIVE_PATH = Path(".para-kb/runtime/telemetry.lock")
SOURCE_RE = re.compile(r"[^A-Za-z0-9._-]+")
ID_RE = re.compile(r"[^A-Za-z0-9._:-]+")
PATH_FIELDS = {
    "vault_paths",
    "entrypoints",
    "documents_read_paths",
    "reference_paths",
    "created_paths",
    "updated_paths",
    "moved_from_paths",
    "moved_to_paths",
    "index_paths",
}
FORBIDDEN_FIELDS = {
    "prompt",
    "query",
    "question",
    "answer",
    "note_body",
    "body",
    "excerpt",
    "raw_input",
    "raw_output",
    "tool_input",
    "tool_output",
    "transcript_path",
}
ALLOWED_EVENT_FIELDS = {
    "schema",
    "schema_version",
    "event",
    "timestamp",
    "source",
    "operation_id",
    "operation_kind",
    "request_id",
    "session_id",
    "source_kind",
    "sequence",
    "tool_name",
    "vault_paths",
    "duration_ms",
    "operation_elapsed_ms",
    "turn_elapsed_ms",
    "input_tokens",
    "output_tokens",
    "token_total_for_analysis",
    "token_is_operation_delta",
    "token_reliability",
    "request_type",
    "route",
    "entrypoints",
    "documents_read_count",
    "documents_read_paths",
    "search_step_count",
    "confidence",
    "operation_type",
    "kb_ingest_used",
    "reference_paths",
    "created_paths",
    "updated_paths",
    "moved_from_paths",
    "moved_to_paths",
    "index_paths",
    "link_pairs",
    "links_added",
    "backlinks_added",
    "frontmatter_completed",
    "summaries_completed",
    "validation",
}
EVENT_NAMES = {
    "QueryStart",
    "OperationStep",
    "QuerySummary",
    "QueryComplete",
    "BuildStart",
    "BuildSummary",
    "BuildComplete",
    "Stop",
}
NULLABLE_COUNT_FIELDS = {
    "duration_ms",
    "operation_elapsed_ms",
    "turn_elapsed_ms",
    "input_tokens",
    "output_tokens",
    "token_total_for_analysis",
}
COUNT_FIELDS = {
    "sequence",
    "documents_read_count",
    "search_step_count",
    "links_added",
    "backlinks_added",
    "frontmatter_completed",
    "summaries_completed",
}
ENUM_FIELDS = {
    "operation_kind": {"query", "build", "turn"},
    "source_kind": {"inbox", "direct", "batch", "unknown"},
    "token_reliability": {"high", "medium", "low", "none"},
    "request_type": {"lookup", "synthesis", "maintenance", "write", "mixed", "unknown"},
    "confidence": {"high", "medium", "low", "none"},
    "operation_type": {"create", "update", "move", "archive", "batch", "mixed", "unknown"},
    "validation": {"passed", "partial", "failed", "unknown"},
}
REQUEST_ID_KEYS = ("request_id", "query_id", "turn_id")


@dataclass(frozen=True)
class VaultContext:
    root: Path
    config_path: Path | None
    config: dict[str, Any]

    @property
    def telemetry_path(self) -> Path:
        return self.root / normalize_relative_path(self.config["telemetry"]["active_path"])

    @property
    def archive_dir(self) -> Path:
        return self.root / normalize_relative_path(self.config["telemetry"]["archive_dir"])

    @property
    def state_path(self) -> Path:
        return self.root / STATE_RELATIVE_PATH

    @property
    def lock_path(self) -> Path:
        return self.root / LOCK_RELATIVE_PATH


class TelemetryError(RuntimeError):
    pass


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def iso_now() -> str:
    return utc_now().isoformat().replace("+00:00", "Z")


def parse_time(value: Any) -> dt.datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def sanitize_source(value: Any, fallback: str) -> str:
    source = value.strip() if isinstance(value, str) else fallback
    source = SOURCE_RE.sub("-", source).strip("-")[:80]
    return source or fallback


def sanitize_id(value: Any, fallback: str | None = None) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return fallback
    cleaned = ID_RE.sub("-", value.strip()).strip("-")[:160]
    return cleaned or fallback


def normalize_relative_path(value: Any) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise TelemetryError("path must be a non-empty string")
    normalized = value.replace("\\", "/").strip()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    candidate = Path(normalized)
    if candidate.is_absolute() or ".." in candidate.parts or re.match(r"^[A-Za-z]:", normalized):
        raise TelemetryError("path must be vault-relative")
    return candidate


def ancestors(start: Path) -> Iterator[Path]:
    current = start.resolve()
    if current.is_file():
        current = current.parent
    while True:
        yield current
        if current.parent == current:
            return
        current = current.parent


def detect_vault_root(start: Path) -> Path | None:
    for directory in ancestors(start):
        if (directory / ".obsidian").is_dir():
            return directory
    return None


def default_config(root: Path) -> dict[str, Any]:
    numbered = all((root / name).exists() for name in ("1. Projects", "2. Areas", "3. Resources", "4. Archive"))
    standard = all((root / name).exists() for name in ("Projects", "Areas", "Resources", "Archive"))
    if numbered:
        roots = {
            "common": "0. Common/",
            "projects": "1. Projects/",
            "areas": "2. Areas/",
            "resources": "3. Resources/",
            "archive": "4. Archive/",
            "inbox": "Inbox/",
        }
    elif standard:
        roots = {
            "common": "Common/",
            "projects": "Projects/",
            "areas": "Areas/",
            "resources": "Resources/",
            "archive": "Archive/",
            "inbox": "Inbox/",
        }
    else:
        raise TelemetryError("no recognizable PARA roots; create .para-kb/config.json")
    common = roots["common"]
    return {
        "schema_version": 1,
        "para_roots": roots,
        "index_file_names": ["index.md", "_index.md"],
        "spine_paths": ["CLAUDE.md", "AGENTS.md", f"{common}index.md", f"{common}log.md"],
        "telemetry": {
            "enabled": True,
            "active_path": f"{common}.telemetry/query-telemetry.jsonl",
            "archive_dir": f"{common}.telemetry/archive",
            "max_bytes": 5 * 1024 * 1024,
            "max_archives": 4,
        },
        "privacy": {"content": "never", "paths": "vault-relative"},
        "exclusions": [".para-kb/", ".obsidian/", ".trash/", f"{common}.telemetry/"],
        "consumer_profile": "para-kb-v1",
    }


def validate_config(config: Any) -> dict[str, Any]:
    if not isinstance(config, dict):
        raise TelemetryError("config must be a JSON object")
    if config.get("schema_version") != 1:
        raise TelemetryError("unsupported config schema_version")
    roots = config.get("para_roots")
    if not isinstance(roots, dict):
        raise TelemetryError("para_roots must be an object")
    for key in ("common", "projects", "areas", "resources", "archive"):
        normalize_relative_path(roots.get(key))
    if roots.get("inbox"):
        normalize_relative_path(roots["inbox"])
    telemetry = config.get("telemetry")
    if not isinstance(telemetry, dict):
        raise TelemetryError("telemetry must be an object")
    if not isinstance(telemetry.get("enabled"), bool):
        raise TelemetryError("telemetry.enabled must be boolean")
    normalize_relative_path(telemetry.get("active_path"))
    normalize_relative_path(telemetry.get("archive_dir"))
    for key, minimum, maximum in (("max_bytes", 65536, 104857600), ("max_archives", 0, 100)):
        value = telemetry.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < minimum or value > maximum:
            raise TelemetryError(f"telemetry.{key} is outside the supported range")
    privacy = config.get("privacy")
    if privacy != {"content": "never", "paths": "vault-relative"}:
        raise TelemetryError("privacy must be content=never and paths=vault-relative")
    if config.get("consumer_profile") != "para-kb-v1":
        raise TelemetryError("consumer_profile must be para-kb-v1")
    for field in ("index_file_names", "spine_paths", "exclusions"):
        value = config.get(field)
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise TelemetryError(f"{field} must be a string array")
    for name in config["index_file_names"]:
        path = normalize_relative_path(name)
        if len(path.parts) != 1 or path.suffix.lower() != ".md":
            raise TelemetryError("index_file_names must contain Markdown filenames, not paths")
    for field in ("spine_paths", "exclusions"):
        for item in config[field]:
            normalize_relative_path(item)
    return config


def load_context(config_arg: str | None, cwd_arg: str | None, allow_auto: bool = True) -> VaultContext:
    start = Path(cwd_arg or os.environ.get("PARA_KB_CWD") or os.getcwd())
    explicit = config_arg or os.environ.get("PARA_KB_CONFIG")
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit).expanduser())
    else:
        candidates.extend(directory / CONFIG_RELATIVE_PATH for directory in ancestors(start))
    for candidate in candidates:
        if not candidate.is_file():
            continue
        root = candidate.resolve().parent.parent
        if not (root / ".obsidian").is_dir():
            raise TelemetryError("config is not inside an Obsidian vault")
        with candidate.open("r", encoding="utf-8") as handle:
            config = validate_config(json.load(handle))
        return VaultContext(root=root, config_path=candidate.resolve(), config=config)
    if allow_auto:
        root = detect_vault_root(start)
        if root is not None:
            return VaultContext(root=root, config_path=None, config=validate_config(default_config(root)))
    raise TelemetryError("no PARA Knowledge Base vault/config found")


def read_payload() -> dict[str, Any]:
    if sys.stdin.isatty():
        return {}
    text = sys.stdin.read().strip()
    if not text:
        return {}
    try:
        value = json.loads(text)
    except json.JSONDecodeError as error:
        raise TelemetryError(f"invalid JSON input: {error.msg}") from error
    if not isinstance(value, dict):
        raise TelemetryError("input must be a JSON object")
    return value


def safe_relative_path(value: Any, context: VaultContext) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip().replace("\\", "/")
    candidate = Path(text).expanduser()
    if candidate.is_absolute():
        try:
            candidate = candidate.resolve().relative_to(context.root.resolve())
        except (OSError, ValueError):
            return None
    try:
        relative = normalize_relative_path(candidate.as_posix()).as_posix()
    except TelemetryError:
        return None
    excluded = [item.replace("$CONFIG_DIR", ".obsidian").rstrip("/") for item in context.config["exclusions"]]
    if any(relative == prefix or relative.startswith(f"{prefix}/") for prefix in excluded if prefix):
        return None
    return relative


def safe_paths(value: Any, context: VaultContext) -> list[str]:
    values = value if isinstance(value, list) else []
    result: list[str] = []
    for item in values:
        path = safe_relative_path(item, context)
        if path and path not in result:
            result.append(path)
    return result[:500]


def safe_link_pairs(value: Any, context: VaultContext) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    result: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        source = safe_relative_path(item.get("source_path") or item.get("source"), context)
        target = safe_relative_path(item.get("target_path") or item.get("target"), context)
        if not source or not target or not source.endswith(".md") or not target.endswith(".md"):
            continue
        pair = {"source_path": source, "target_path": target}
        if pair not in result:
            result.append(pair)
    return result[:100]


def nonnegative_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and value >= 0:
        return int(round(value))
    return None


def string_choice(value: Any, choices: set[str], fallback: str) -> str:
    return value if isinstance(value, str) and value in choices else fallback


def base_event(event: str, kind: str, source: Any, operation: dict[str, Any] | None = None) -> dict[str, Any]:
    record: dict[str, Any] = {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "event": event,
        "timestamp": iso_now(),
        "source": sanitize_source(source, "para-kb"),
        "operation_kind": kind,
    }
    if operation:
        record["operation_id"] = operation["operation_id"]
        if operation.get("request_id"):
            record["request_id"] = operation["request_id"]
        if operation.get("session_id"):
            record["session_id"] = operation["session_id"]
    return record


def default_state() -> dict[str, Any]:
    return {"schema_version": 1, "current_request": None, "active_operations": []}


def load_state(context: VaultContext) -> dict[str, Any]:
    try:
        with context.state_path.open("r", encoding="utf-8") as handle:
            state = json.load(handle)
        if not isinstance(state, dict) or not isinstance(state.get("active_operations"), list):
            return default_state()
        cutoff = utc_now() - dt.timedelta(hours=24)
        state["active_operations"] = [
            item for item in state["active_operations"]
            if isinstance(item, dict) and (parse_time(item.get("started_at")) or cutoff) >= cutoff
        ]
        return state
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default_state()


def write_state(context: VaultContext, state: dict[str, Any]) -> None:
    context.state_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = context.state_path.with_suffix(f".tmp-{os.getpid()}")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(state, handle, ensure_ascii=False, separators=(",", ":"))
        handle.write("\n")
    os.replace(temporary, context.state_path)


@contextlib.contextmanager
def locked(context: VaultContext) -> Iterator[None]:
    context.lock_path.parent.mkdir(parents=True, exist_ok=True)
    with context.lock_path.open("a+", encoding="utf-8") as handle:
        if fcntl is not None:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def rotate_if_needed(context: VaultContext, incoming_bytes: int) -> None:
    path = context.telemetry_path
    limit = context.config["telemetry"]["max_bytes"]
    if not path.exists() or path.stat().st_size + incoming_bytes <= limit:
        return
    archive_dir = context.archive_dir
    archive_dir.mkdir(parents=True, exist_ok=True)
    stamp = utc_now().strftime("%Y%m%dT%H%M%SZ")
    archive = archive_dir / f"{path.stem}-{stamp}-{uuid.uuid4().hex[:6]}.jsonl"
    os.replace(path, archive)
    archives = sorted(archive_dir.glob("*.jsonl"), key=lambda item: item.stat().st_mtime, reverse=True)
    keep = context.config["telemetry"]["max_archives"]
    for stale in archives[keep:]:
        stale.unlink(missing_ok=True)


def append_event(context: VaultContext, event: dict[str, Any]) -> None:
    if not context.config["telemetry"]["enabled"]:
        return
    sanitized = sanitize_event(event, context)
    encoded = (json.dumps(sanitized, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    context.telemetry_path.parent.mkdir(parents=True, exist_ok=True)
    rotate_if_needed(context, len(encoded))
    with context.telemetry_path.open("ab") as handle:
        handle.write(encoded)


def sanitize_event(event: dict[str, Any], context: VaultContext) -> dict[str, Any]:
    if FORBIDDEN_FIELDS.intersection(event):
        raise TelemetryError("event contains forbidden content fields")
    if (
        event.get("schema") != SCHEMA
        or type(event.get("schema_version")) is not int
        or event.get("schema_version") != SCHEMA_VERSION
    ):
        raise TelemetryError("event schema is unsupported")
    if event.get("event") not in EVENT_NAMES:
        raise TelemetryError("event type is unsupported")
    if parse_time(event.get("timestamp")) is None:
        raise TelemetryError("event timestamp is invalid")
    clean: dict[str, Any] = {}
    for key, value in event.items():
        if key not in ALLOWED_EVENT_FIELDS:
            continue
        if key in PATH_FIELDS:
            clean[key] = safe_paths(value, context)
        elif key == "link_pairs":
            clean[key] = safe_link_pairs(value, context)
        elif key in {"schema", "schema_version", "event", "timestamp"}:
            clean[key] = value
        elif key == "source":
            clean[key] = sanitize_source(value, "para-kb")
        elif key in {"operation_id", "request_id", "session_id"}:
            identifier = sanitize_id(value)
            if identifier:
                clean[key] = identifier
        elif key == "tool_name":
            clean[key] = sanitize_source(value, "tool")[:120]
        elif key in ENUM_FIELDS:
            if isinstance(value, str) and value in ENUM_FIELDS[key]:
                clean[key] = value
        elif key in NULLABLE_COUNT_FIELDS:
            clean[key] = nonnegative_int(value) if value is not None else None
        elif key in COUNT_FIELDS:
            number = nonnegative_int(value)
            if number is not None:
                clean[key] = number
        elif key in {"token_is_operation_delta", "kb_ingest_used"}:
            if isinstance(value, bool):
                clean[key] = value
        elif key == "route":
            if isinstance(value, str):
                clean[key] = value.strip()[:120]
            elif isinstance(value, list):
                clean[key] = list(dict.fromkeys(
                    item.strip()[:120] for item in value if isinstance(item, str) and item.strip()
                ))
    if "source" not in clean or "operation_kind" not in clean:
        raise TelemetryError("event source and operation_kind are required")
    if clean.get("event") != "Stop" and "operation_id" not in clean:
        raise TelemetryError("operation event requires operation_id")
    return clean


def has_explicit_request_identity(payload: dict[str, Any]) -> bool:
    return any(isinstance(payload.get(key), str) and payload.get(key, "").strip() for key in REQUEST_ID_KEYS)


def request_identity(payload: dict[str, Any], state: dict[str, Any]) -> tuple[str, str | None]:
    current = state.get("current_request") if isinstance(state.get("current_request"), dict) else {}
    request_id = sanitize_id(
        payload.get("request_id") or payload.get("query_id") or payload.get("turn_id") or current.get("request_id"),
        f"request-{uuid.uuid4().hex}",
    )
    session_id = sanitize_id(
        payload.get("session_id") or payload.get("conversation_id") or current.get("session_id")
    )
    return request_id or f"request-{uuid.uuid4().hex}", session_id


def operation_for(state: dict[str, Any], operation_id: Any) -> dict[str, Any] | None:
    clean_id = sanitize_id(operation_id)
    if not clean_id:
        return None
    return next((item for item in state["active_operations"] if item.get("operation_id") == clean_id), None)


def usage_snapshot(payload: dict[str, Any]) -> dict[str, int | None]:
    usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
    input_tokens = nonnegative_int(payload.get("input_tokens") or usage.get("input_tokens") or usage.get("prompt_tokens"))
    output_tokens = nonnegative_int(payload.get("output_tokens") or usage.get("output_tokens") or usage.get("completion_tokens"))
    total_tokens = nonnegative_int(payload.get("total_tokens") or usage.get("total_tokens"))
    if total_tokens is None and input_tokens is not None and output_tokens is not None:
        total_tokens = input_tokens + output_tokens
    return {"input_tokens": input_tokens, "output_tokens": output_tokens, "total_tokens": total_tokens}


def usage_delta(start: dict[str, Any], end: dict[str, Any]) -> dict[str, int | None]:
    result: dict[str, int | None] = {}
    for key in ("input_tokens", "output_tokens", "total_tokens"):
        before = nonnegative_int(start.get(key))
        after = nonnegative_int(end.get(key))
        result[key] = after - before if before is not None and after is not None and after >= before else None
    return result


def start_operation(context: VaultContext, payload: dict[str, Any], kind: str) -> dict[str, Any]:
    with locked(context):
        state = load_state(context)
        request_id, session_id = request_identity(payload, state)
        operation_id = sanitize_id(payload.get("operation_id"), f"{kind}-{uuid.uuid4().hex}")
        operation = {
            "operation_id": operation_id,
            "kind": kind,
            "request_id": request_id,
            "session_id": session_id,
            "started_at": iso_now(),
            "source": sanitize_source(payload.get("source"), f"kb-{kind}-skill"),
            "sequence": 0,
            "summary_written": False,
            "usage_start": usage_snapshot(payload),
        }
        state["active_operations"] = [
            item for item in state["active_operations"] if item.get("operation_id") != operation_id
        ] + [operation]
        event_name = "QueryStart" if kind == "query" else "BuildStart"
        event = base_event(event_name, kind, operation["source"], operation)
        if kind == "build":
            event["source_kind"] = string_choice(
                payload.get("source_kind"), {"inbox", "direct", "batch", "unknown"}, "unknown"
            )
        append_event(context, event)
        write_state(context, state)
    return {"ok": True, "operation_id": operation_id, "request_id": request_id, "query_id": request_id}


def write_query_summary(context: VaultContext, payload: dict[str, Any]) -> dict[str, Any]:
    with locked(context):
        state = load_state(context)
        operation = operation_for(state, payload.get("operation_id"))
        if operation is None or operation.get("kind") != "query":
            raise TelemetryError("query summary requires an active exact operation_id")
        documents = safe_paths(payload.get("documents_read_paths"), context)
        entrypoints = safe_paths(payload.get("entrypoints"), context)
        route = payload.get("route")
        if isinstance(route, list):
            route = [str(item)[:120] for item in route if isinstance(item, str) and item.strip()]
        elif not isinstance(route, str):
            route = []
        event = base_event("QuerySummary", "query", payload.get("source") or operation["source"], operation)
        event.update({
            "request_type": string_choice(
                payload.get("request_type"), {"lookup", "synthesis", "maintenance", "write", "mixed", "unknown"}, "unknown"
            ),
            "route": route,
            "entrypoints": entrypoints,
            "documents_read_count": nonnegative_int(payload.get("documents_read_count")) or len(documents),
            "documents_read_paths": documents,
            "search_step_count": nonnegative_int(payload.get("search_step_count")) or 0,
            "confidence": string_choice(payload.get("confidence"), {"high", "medium", "low", "none"}, "none"),
        })
        append_event(context, event)
        operation["summary_written"] = True
        operation["summary_at"] = event["timestamp"]
        write_state(context, state)
    return {"ok": True, "operation_id": operation["operation_id"]}


def write_build_summary(context: VaultContext, payload: dict[str, Any]) -> dict[str, Any]:
    with locked(context):
        state = load_state(context)
        operation = operation_for(state, payload.get("operation_id"))
        if operation is None or operation.get("kind") != "build":
            raise TelemetryError("build summary requires an active exact operation_id")
        event = base_event("BuildSummary", "build", payload.get("source") or operation["source"], operation)
        event.update({
            "operation_type": string_choice(
                payload.get("operation_type"), {"create", "update", "move", "archive", "batch", "mixed", "unknown"}, "unknown"
            ),
            "route": str(payload.get("route"))[:120] if isinstance(payload.get("route"), str) else "kb-ingest",
            "kb_ingest_used": payload.get("kb_ingest_used") is True,
            "reference_paths": safe_paths(payload.get("reference_paths"), context),
            "created_paths": safe_paths(payload.get("created_paths"), context),
            "updated_paths": safe_paths(payload.get("updated_paths"), context),
            "moved_from_paths": safe_paths(payload.get("moved_from_paths"), context),
            "moved_to_paths": safe_paths(payload.get("moved_to_paths"), context),
            "index_paths": safe_paths(payload.get("index_paths"), context),
            "link_pairs": safe_link_pairs(payload.get("link_pairs"), context),
            "links_added": nonnegative_int(payload.get("links_added")) or 0,
            "backlinks_added": nonnegative_int(payload.get("backlinks_added")) or 0,
            "frontmatter_completed": nonnegative_int(payload.get("frontmatter_completed")) or 0,
            "summaries_completed": nonnegative_int(payload.get("summaries_completed")) or 0,
            "validation": string_choice(payload.get("validation"), {"passed", "partial", "failed", "unknown"}, "unknown"),
            "confidence": string_choice(payload.get("confidence"), {"high", "medium", "low", "none"}, "none"),
        })
        append_event(context, event)
        operation["summary_written"] = True
        operation["summary_at"] = event["timestamp"]
        write_state(context, state)
    return {"ok": True, "operation_id": operation["operation_id"]}


def tool_name(payload: dict[str, Any]) -> str | None:
    for key in ("tool_name", "tool", "name"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return sanitize_source(value, "tool")[:120]
    return None


def extract_hook_paths(payload: dict[str, Any], context: VaultContext) -> list[str]:
    candidates: list[Any] = []
    for container_key in ("tool_input", "tool_response", "input", "output"):
        container = payload.get(container_key)
        if not isinstance(container, dict):
            continue
        for key in ("path", "file", "file_path", "paths", "files", "vault_paths"):
            value = container.get(key)
            candidates.extend(value if isinstance(value, list) else [value])
    for key in ("path", "file", "file_path", "paths", "files", "vault_paths"):
        value = payload.get(key)
        candidates.extend(value if isinstance(value, list) else [value])
    result: list[str] = []
    for candidate in candidates:
        path = safe_relative_path(candidate, context)
        if path and (path.endswith(".md") or path.endswith(".jsonl")) and path not in result:
            result.append(path)
    return result[:50]


def hook_userprompt(context: VaultContext, payload: dict[str, Any]) -> None:
    with locked(context):
        state = load_state(context)
        request_id, session_id = request_identity(payload, state)
        state["current_request"] = {
            "request_id": request_id,
            "session_id": session_id,
            "started_at": iso_now(),
            "usage_start": usage_snapshot(payload),
        }
        write_state(context, state)


def hook_posttool(context: VaultContext, payload: dict[str, Any]) -> None:
    with locked(context):
        state = load_state(context)
        request_id, _ = request_identity(payload, state)
        candidates = [item for item in state["active_operations"] if item.get("request_id") == request_id]
        if (
            not candidates
            and not has_explicit_request_identity(payload)
            and state.get("current_request") is None
            and len(state["active_operations"]) == 1
        ):
            candidates = state["active_operations"]
        if not candidates:
            return
        operation = candidates[-1]
        paths = extract_hook_paths(payload, context)
        name = tool_name(payload)
        if not paths and not name:
            return
        operation["sequence"] = int(operation.get("sequence", 0)) + 1
        event = base_event("OperationStep", operation["kind"], "runtime-hook", operation)
        event.update({
            "sequence": operation["sequence"],
            "tool_name": name or "tool",
            "vault_paths": paths,
        })
        duration = nonnegative_int(payload.get("duration_ms") or payload.get("elapsed_ms"))
        if duration is not None:
            event["duration_ms"] = duration
        append_event(context, event)
        write_state(context, state)


def hook_stop(context: VaultContext, payload: dict[str, Any]) -> None:
    with locked(context):
        state = load_state(context)
        request_id, session_id = request_identity(payload, state)
        matching = [item for item in state["active_operations"] if item.get("request_id") == request_id]
        if not matching and not has_explicit_request_identity(payload) and state.get("current_request") is None:
            request_ids = {item.get("request_id") for item in state["active_operations"]}
            if len(request_ids) == 1:
                matching = list(state["active_operations"])
        current = state.get("current_request") if isinstance(state.get("current_request"), dict) else None
        if not matching:
            if current and current.get("request_id") == request_id:
                state["current_request"] = None
                write_state(context, state)
            return
        finalized = [item for item in matching if item.get("summary_written") is True]
        end_usage = usage_snapshot(payload)
        for operation in finalized:
            started = parse_time(operation.get("started_at"))
            elapsed = max(0, int((utc_now() - started).total_seconds() * 1000)) if started else None
            event_name = "QueryComplete" if operation["kind"] == "query" else "BuildComplete"
            event = base_event(event_name, operation["kind"], "runtime-hook", operation)
            event["operation_elapsed_ms"] = elapsed
            if len(finalized) == 1:
                delta = usage_delta(operation.get("usage_start") or {}, end_usage)
                reliable = delta["total_tokens"] is not None
                event.update({
                    "input_tokens": delta["input_tokens"],
                    "output_tokens": delta["output_tokens"],
                    "token_total_for_analysis": delta["total_tokens"],
                    "token_is_operation_delta": reliable,
                    "token_reliability": "high" if reliable else "none",
                })
            else:
                event.update({
                    "input_tokens": None,
                    "output_tokens": None,
                    "token_total_for_analysis": None,
                    "token_is_operation_delta": False,
                    "token_reliability": "none",
                })
            append_event(context, event)
        stop = base_event("Stop", "turn", "runtime-hook")
        stop["request_id"] = request_id
        if session_id:
            stop["session_id"] = session_id
        current_start = parse_time(current.get("started_at")) if current else None
        stop["turn_elapsed_ms"] = max(0, int((utc_now() - current_start).total_seconds() * 1000)) if current_start else None
        append_event(context, stop)
        stopped_ids = {item["operation_id"] for item in matching}
        state["active_operations"] = [
            item for item in state["active_operations"] if item.get("operation_id") not in stopped_ids
        ]
        if current and current.get("request_id") == request_id:
            state["current_request"] = None
        write_state(context, state)


def initialize_config(cwd_arg: str | None, profile: str) -> dict[str, Any]:
    start = Path(cwd_arg or os.getcwd())
    root = detect_vault_root(start)
    if root is None:
        raise TelemetryError("no parent .obsidian directory found")
    path = root / CONFIG_RELATIVE_PATH
    if path.exists():
        with path.open("r", encoding="utf-8") as handle:
            validate_config(json.load(handle))
        return {"ok": True, "path": path.relative_to(root).as_posix(), "created": False}
    config = default_config_for_profile(root, profile)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(config, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return {"ok": True, "path": path.relative_to(root).as_posix(), "created": True}


def default_config_for_profile(root: Path, profile: str) -> dict[str, Any]:
    if profile == "auto":
        return default_config(root)
    names = {
        "numbered": ("0. Common", "1. Projects", "2. Areas", "3. Resources", "4. Archive"),
        "standard": ("Common", "Projects", "Areas", "Resources", "Archive"),
    }.get(profile)
    if names is None:
        raise TelemetryError("profile must be auto, numbered, or standard")
    common, projects, areas, resources, archive = names
    config = {
        "schema_version": 1,
        "para_roots": {
            "common": f"{common}/",
            "projects": f"{projects}/",
            "areas": f"{areas}/",
            "resources": f"{resources}/",
            "archive": f"{archive}/",
            "inbox": "Inbox/",
        },
        "index_file_names": ["index.md", "_index.md"],
        "spine_paths": ["CLAUDE.md", "AGENTS.md", f"{common}/index.md", f"{common}/log.md"],
        "telemetry": {
            "enabled": True,
            "active_path": f"{common}/.telemetry/query-telemetry.jsonl",
            "archive_dir": f"{common}/.telemetry/archive",
            "max_bytes": 5 * 1024 * 1024,
            "max_archives": 4,
        },
        "privacy": {"content": "never", "paths": "vault-relative"},
        "exclusions": [".para-kb/", ".obsidian/", ".trash/", f"{common}/.telemetry/"],
        "consumer_profile": "para-kb-v1",
    }
    return validate_config(config)


def sanitize_file(context: VaultContext, input_path: Path, output_path: Path) -> dict[str, Any]:
    written = 0
    skipped = 0
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with input_path.open("r", encoding="utf-8") as source, output_path.open("w", encoding="utf-8") as target:
        for line in source:
            try:
                raw = json.loads(line)
                if not isinstance(raw, dict):
                    raise ValueError("not an object")
                clean = sanitize_event(raw, context)
                target.write(json.dumps(clean, ensure_ascii=False, separators=(",", ":")) + "\n")
                written += 1
            except (json.JSONDecodeError, TelemetryError, ValueError):
                skipped += 1
    return {"ok": True, "written": written, "skipped": skipped}


def command_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config")
    parser.add_argument("--cwd")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("query-start", "query-summary", "query-complete", "build-start", "build-summary", "build-complete"):
        subparsers.add_parser(name)
    hook = subparsers.add_parser("hook")
    hook.add_argument("kind", choices=("userprompt", "posttool", "stop"))
    init = subparsers.add_parser("init-config")
    init.add_argument("--profile", choices=("auto", "numbered", "standard"), default="auto")
    subparsers.add_parser("validate-config")
    sanitize = subparsers.add_parser("sanitize")
    sanitize.add_argument("input")
    sanitize.add_argument("output")
    return parser


def run(argv: list[str] | None = None) -> int:
    args = command_parser().parse_args(argv)
    try:
        if args.command == "init-config":
            result = initialize_config(args.cwd, args.profile)
        else:
            context = load_context(args.config, args.cwd)
            if args.command == "validate-config":
                result = {
                    "ok": True,
                    "config": context.config_path.relative_to(context.root).as_posix() if context.config_path else "auto",
                    "consumer_profile": context.config["consumer_profile"],
                }
            elif args.command == "sanitize":
                result = sanitize_file(context, Path(args.input), Path(args.output))
            else:
                payload = read_payload()
                if args.command == "query-start":
                    result = start_operation(context, payload, "query")
                elif args.command in {"query-summary", "query-complete"}:
                    if args.command == "query-complete":
                        print("query-complete is deprecated; use query-summary", file=sys.stderr)
                    result = write_query_summary(context, payload)
                elif args.command == "build-start":
                    result = start_operation(context, payload, "build")
                elif args.command in {"build-summary", "build-complete"}:
                    if args.command == "build-complete":
                        print("build-complete is deprecated; use build-summary", file=sys.stderr)
                    result = write_build_summary(context, payload)
                elif args.command == "hook":
                    if args.kind == "userprompt":
                        hook_userprompt(context, payload)
                    elif args.kind == "posttool":
                        hook_posttool(context, payload)
                    else:
                        hook_stop(context, payload)
                    result = {}
                else:  # pragma: no cover
                    raise TelemetryError("unsupported command")
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
        return 0
    except (TelemetryError, OSError, json.JSONDecodeError) as error:
        if args.command == "hook":
            print("{}")
            return 0
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(run())
