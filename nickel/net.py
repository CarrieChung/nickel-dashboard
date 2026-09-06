import shutil
import subprocess

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


def fetch(url, timeout=8, headers=None):
    body = _fetch_with_curl(url, timeout, headers)
    return body


def _fetch_with_curl(url, timeout, headers):
    if not shutil.which("curl"):
        return _fetch_with_requests(url, timeout, headers)
    cmd = [
        "curl", "-fsS",
        "--max-time", str(max(2, int(timeout) + 1)),
        "--connect-timeout", "3",
        "-A", UA,
        "-L",
        "--http1.1",
    ]
    for key, value in (headers or {}).items():
        cmd += ["-H", f"{key}: {value}"]
    cmd.append(url)
    proc = subprocess.run(cmd, capture_output=True, timeout=max(3, timeout + 2))
    if proc.returncode != 0:
        raise RuntimeError(f"fetch failed ({proc.returncode})")
    return proc.stdout


def _fetch_with_requests(url, timeout, headers):
    import requests

    ua_headers = {"User-Agent": UA}
    if headers:
        ua_headers.update(headers)
    resp = requests.get(url, headers=ua_headers, timeout=(3.05, timeout))
    resp.raise_for_status()
    return resp.content