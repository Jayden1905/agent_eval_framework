"""Bring up cloudflared tunnel, spawn sandbox with tunnel host on allow_list,
have sandbox curl the tunnel URL. If this works, option E is viable end-to-end.
"""
import os
import re
import subprocess
import time
import urllib.parse
from dotenv import load_dotenv

load_dotenv()

# 1. Start cloudflared tunnel
print("==> starting cloudflared quick tunnel")
cf = subprocess.Popen(
    ["cloudflared", "tunnel", "--url", "http://localhost:8000"],
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
)

url = ""
pat = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")
deadline = time.time() + 30
while time.time() < deadline:
    line = cf.stdout.readline()
    if not line:
        time.sleep(0.2)
        continue
    m = pat.search(line)
    if m:
        url = m.group(0)
        print(f"    tunnel: {url}")
        break

if not url:
    cf.terminate()
    raise SystemExit("cloudflared didn't report a URL")

host = urllib.parse.urlparse(url).hostname
print(f"    host: {host}")
print("    (skipping mac-side probe since corporate DNS is known-broken)")
print("    (relying on daytona sandbox DNS instead)")

# 2. Spawn sandbox with tunnel host allowlisted
try:
    from daytona import Daytona, CreateSandboxFromImageParams, Image, Resources, FileUpload
    d = Daytona()
    img = Image.base("python:3.11-slim").pip_install(["httpx"])
    params = CreateSandboxFromImageParams(
        image=img, language="python",
        resources=Resources(cpu=1, memory=2),
        auto_stop_interval=0, auto_delete_interval=5,
        domain_allow_list=host,
    )
    print("==> spawning sandbox with allowlist")
    sb = d.create(params, timeout=180)
    print(f"    sandbox: {sb.id}")

    probe = f"""
import httpx, socket, time
host = {host!r}
url = {url!r}

# retry DNS a few times — cloudflare edge propagation can lag
for i in range(1, 11):
    try:
        ip = socket.gethostbyname(host)
        print(f"DNS t={{i*2}}s: {{host}} -> {{ip}}")
        break
    except Exception as e:
        print(f"DNS t={{i*2}}s FAIL: {{e}}")
        time.sleep(2)

# hit the tunnel /api/health
for i in range(1, 11):
    try:
        r = httpx.get(url + "/api/health", timeout=10)
        print(f"HTTP t={{i*2}}s: {{r.status_code}} {{r.text}}")
        break
    except Exception as e:
        print(f"HTTP t={{i*2}}s FAIL: {{type(e).__name__}}: {{e}}")
        time.sleep(2)

# hit an agent card
try:
    r = httpx.get(url + "/agents/accurate/.well-known/agent-card.json", timeout=10)
    print(f"agent-card: {{r.status_code}} {{r.text[:200]}}")
except Exception as e:
    print(f"agent-card FAIL: {{e}}")
"""

    sb.process.exec("mkdir -p /work")
    sb.fs.upload_files([FileUpload(source=probe.encode(), destination="/work/p.py")])
    result = sb.process.exec("cd /work && python p.py", timeout=120)
    print("--- sandbox output ---")
    print(getattr(result, "result", result))
    d.delete(sb)
    print("--- sandbox deleted ---")
finally:
    cf.terminate()
    try:
        cf.wait(timeout=3)
    except subprocess.TimeoutExpired:
        cf.kill()
    print("--- cloudflared stopped ---")
