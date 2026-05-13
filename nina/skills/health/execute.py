import time as _time

_start_time: float = _time.time()


def mark_start() -> None:
    global _start_time
    _start_time = _time.time()


def get_status() -> dict:
    uptime = int(_time.time() - _start_time)
    hours, remainder = divmod(uptime, 3600)
    minutes, seconds = divmod(remainder, 60)
    return {
        "status": "ok",
        "uptime": f"{hours:02d}:{minutes:02d}:{seconds:02d}",
        "uptime_seconds": uptime,
    }
