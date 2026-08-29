"""Try setting domain_allow_list on the sandbox to unblock the Nosana host."""
import os
import urllib.parse
from dotenv import load_dotenv

load_dotenv()

from daytona import Daytona, CreateSandboxFromImageParams, Image, Resources, FileUpload

NOSANA_HOST = urllib.parse.urlparse(os.environ["NOSANA_BASE_URL"]).hostname
print(f"trying domain_allow_list='{NOSANA_HOST}'")

d = Daytona()
img = Image.base("python:3.11-slim").pip_install(["httpx"])
params = CreateSandboxFromImageParams(
    image=img,
    language="python",
    env_vars={
        "OPENAI_BASE_URL": os.environ["NOSANA_BASE_URL"],
        "OPENAI_API_KEY": os.environ.get("NOSANA_API_KEY") or "nosana-no-auth",
    },
    resources=Resources(cpu=1, memory=2),
    auto_stop_interval=0,
    auto_delete_interval=5,
    domain_allow_list=NOSANA_HOST,
)

try:
    sb = d.create(params, timeout=180)
    print("sandbox up:", sb.id)
except Exception as e:
    print(f"CREATE FAILED: {type(e).__name__}: {e}")
    raise SystemExit(1)

probe = r"""
import os, httpx
url = os.environ["OPENAI_BASE_URL"].rstrip("/") + "/models"
try:
    r = httpx.get(url, timeout=15)
    print(f"GET {url} -> {r.status_code}")
    print("body:", r.text[:300])
except Exception as e:
    print(f"FAIL: {type(e).__name__}: {e}")
"""

try:
    sb.process.exec("mkdir -p /work")
    sb.fs.upload_files([FileUpload(source=probe.encode(), destination="/work/p.py")])
    result = sb.process.exec("cd /work && python p.py")
    print("--- exit:", getattr(result, "exit_code", "?"))
    print(getattr(result, "result", result))
finally:
    d.delete(sb)
    print("sandbox deleted")
