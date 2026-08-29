"""Spawn a Daytona sandbox, ask "what's my public IP", print it.

Run this a few times — if the IP changes across runs, Daytona is rotating from
a pool and you'll need the pool CIDR from Daytona instead of a single IP.
"""
import os
from dotenv import load_dotenv

load_dotenv()

from daytona import Daytona, CreateSandboxFromImageParams, Image, Resources, FileUpload

d = Daytona()
img = Image.base("python:3.11-slim").pip_install(["httpx"])
params = CreateSandboxFromImageParams(
    image=img,
    language="python",
    resources=Resources(cpu=1, memory=2),
    auto_stop_interval=0,
    auto_delete_interval=5,
)
sb = d.create(params, timeout=180)
print("sandbox up:", sb.id)

probe = r"""
import httpx
tests = [
    ("http",  "http://api.ipify.org"),
    ("https", "https://api.ipify.org"),
    ("http",  "http://ifconfig.me/ip"),
    ("https", "https://ifconfig.me/ip"),
    ("http",  "http://checkip.amazonaws.com"),
    ("http",  "http://ip-api.com/line/?fields=query"),
    ("https", "https://one.one.one.one/cdn-cgi/trace"),
    ("https", "https://www.google.com/generate_204"),
]
for scheme, url in tests:
    try:
        r = httpx.get(url, timeout=10, follow_redirects=True)
        body = r.text.strip().split("\n")[0][:80]
        print(f"{scheme:5s} {url:55s} -> {r.status_code} {body}")
    except Exception as e:
        print(f"{scheme:5s} {url:55s} -> FAIL: {type(e).__name__}: {e}")
"""

try:
    sb.process.exec("mkdir -p /work && apt-get update -qq && apt-get install -y -qq curl >/dev/null")
    sb.fs.upload_files([FileUpload(source=probe.encode(), destination="/work/ip.py")])
    result = sb.process.exec("cd /work && python ip.py")
    print("--- egress IP report ---")
    print(getattr(result, "result", result))
finally:
    d.delete(sb)
    print("sandbox deleted")
