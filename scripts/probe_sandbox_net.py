"""Spawn a Daytona sandbox and probe whether it can reach the Nosana endpoint."""
import os
from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault("OPENAI_BASE_URL", os.environ["NOSANA_BASE_URL"])
os.environ.setdefault("OPENAI_API_KEY", os.environ.get("NOSANA_API_KEY") or "nosana-no-auth")

from daytona import Daytona, CreateSandboxFromImageParams, Image, Resources, FileUpload

d = Daytona()
img = Image.base("python:3.11-slim").pip_install(["httpx"])
params = CreateSandboxFromImageParams(
    image=img,
    language="python",
    env_vars={
        "OPENAI_BASE_URL": os.environ["OPENAI_BASE_URL"],
        "OPENAI_API_KEY": os.environ["OPENAI_API_KEY"],
        "NOSANA_MODEL": os.environ["NOSANA_MODEL"],
    },
    resources=Resources(cpu=1, memory=2),
    auto_stop_interval=0,
    auto_delete_interval=5,
)
sb = d.create(params, timeout=180)
print("sandbox up:", sb.id)

probe = r"""
import os, socket, subprocess
import urllib.parse
base = os.environ.get("OPENAI_BASE_URL", "")
host = urllib.parse.urlparse(base).hostname
print(f"HOST: {host}")

try:
    print(f"DNS: {host} -> {socket.gethostbyname(host)}")
except Exception as e:
    print(f"DNS FAIL: {e}")

# curl -v probe: capture full TLS handshake detail
try:
    out = subprocess.run(
        ["curl", "-sSv", "--max-time", "15", f"{base.rstrip('/')}/models"],
        capture_output=True, text=True, timeout=30,
    )
    print(f"curl exit: {out.returncode}")
    print("--- curl stderr ---")
    print(out.stderr)
    print("--- curl stdout ---")
    print(out.stdout[:400])
except Exception as e:
    print(f"curl subprocess FAIL: {e}")
"""

try:
    sb.process.exec("mkdir -p /work && apt-get update -qq && apt-get install -y -qq curl >/dev/null")
    sb.fs.upload_files([FileUpload(source=probe.encode(), destination="/work/probe.py")])
    result = sb.process.exec("cd /work && python probe.py")
    print("--- exit:", getattr(result, "exit_code", "?"))
    print("--- stdout ---")
    print(getattr(result, "result", result))
finally:
    d.delete(sb)
    print("sandbox deleted")
