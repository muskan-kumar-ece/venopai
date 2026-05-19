import json
import logging
import threading
import traceback

_local = threading.local()


def set_request_id(request_id: str) -> None:
    _local.request_id = request_id


def get_request_id() -> str:
    return getattr(_local, "request_id", "-")


def set_context(**kwargs) -> None:
    context = getattr(_local, "context", {})
    context.update(kwargs)
    _local.context = context


def get_context() -> dict:
    return getattr(_local, "context", {})


def clear_context() -> None:
    _local.context = {}
    _local.request_id = "-"


class RequestIDFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        for key, value in get_context().items():
            setattr(record, key, value)
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        from datetime import datetime, timezone as dt_timezone

        payload: dict = {
            "timestamp": datetime.fromtimestamp(record.created, tz=dt_timezone.utc).isoformat(timespec="microseconds"),
            "level": record.levelname,
            "request_id": getattr(record, "request_id", "-"),
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in ("order_id", "payment_id", "user_id", "path", "method", "status_code", "latency_ms"):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["exc_info"] = "".join(traceback.format_exception(*record.exc_info)).rstrip()
        return json.dumps(payload, ensure_ascii=False)
