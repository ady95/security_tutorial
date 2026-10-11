"""Small teaching policy: inspect JSON only; no Docker API calls."""
import argparse
import json
from pathlib import Path


def risks(container):
    host = container.get("HostConfig", {})
    findings = []
    user = str(container.get("Config", {}).get("User", ""))
    if user.split(":")[0] in {"", "0", "root"}:
        findings.append("root-user")
    if host.get("Privileged"):
        findings.append("privileged")
    if not host.get("ReadonlyRootfs"):
        findings.append("writable-rootfs")
    if "ALL" not in (host.get("CapDrop") or []):
        findings.append("capabilities-not-dropped")
    if not any(opt.startswith("no-new-privileges") and not opt.endswith("false") for opt in (host.get("SecurityOpt") or [])):
        findings.append("no-new-privileges-missing")
    for mount in container.get("Mounts", []):
        source = mount.get("Source", "").replace("\\", "/")
        dest = mount.get("Destination", "").replace("\\", "/")
        if source.endswith("/docker.sock") or dest.endswith("/docker.sock"):
            findings.append("docker-socket")
        if source == "/":
            findings.append("host-root-mount")
        if mount.get("Type") == "bind" and mount.get("RW"):
            findings.append("writable-bind")
    return findings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file", type=Path)
    args = parser.parse_args()
    data = json.loads(args.file.read_text(encoding="utf-8-sig"))
    if not isinstance(data, list) or not data or not all(isinstance(item, dict) and "Config" in item and "HostConfig" in item and "Mounts" in item for item in data):
        raise SystemExit("inspect data missing or invalid")
    total = 0
    for item in data:
        found = risks(item)
        total += len(found)
        for finding in found:
            print(item.get("Name", "lab-only-unnamed"), finding)
    print(f"policy findings: {total}")
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
