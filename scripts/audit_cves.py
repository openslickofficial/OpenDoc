"""
Query OSV (Open Source Vulnerabilities) API for known CVEs in Snapdragon Document Assistant dependencies.
Backend used by pip-audit and Google Security.
"""

import json
import urllib.request
import urllib.error

PACKAGES = [
    ("torch", "2.11.0"),
    ("transformers", "5.16.1"),
    ("onnxruntime", "1.22.1"),
    ("pillow", "11.3.0"),
    ("opencv-python", "4.13.0.92"),
    ("numpy", "1.26.4"),
    ("pyside6", "6.11.2"),
    ("piper-tts", "1.8.0"),
]

def query_osv(package_name: str, version: str):
    url = "https://api.osv.dev/v1/query"
    payload = {
        "version": version,
        "package": {
            "name": package_name,
            "ecosystem": "PyPI"
        }
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "SecurityAuditScript/1.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            vulns = data.get("vulns", [])
            return vulns
    except Exception as e:
        return [{"id": "QUERY_ERROR", "details": str(e)}]

def main():
    print("=" * 70)
    print("DEPENDENCY CVE AUDIT VIA OSV / PIP-AUDIT DATABASE")
    print("=" * 70)

    total_vulns = 0
    results = {}

    for name, ver in PACKAGES:
        print(f"Auditing {name}=={ver} ...", end=" ", flush=True)
        vulns = query_osv(name, ver)
        results[name] = {"version": ver, "vulns": vulns}
        if vulns:
            print(f"[!] {len(vulns)} VULNERABILITY(IES) FOUND")
            total_vulns += len(vulns)
            for v in vulns:
                vid = v.get("id", "UNKNOWN")
                summary = v.get("summary", v.get("details", ""))[:140].replace("\n", " ")
                aliases = ", ".join(v.get("aliases", []))
                print(f"   -> {vid} ({aliases}): {summary}")
        else:
            print("[OK] 0 KNOWN CVEs")

    print("\n" + "=" * 70)
    print(f"AUDIT COMPLETE: {total_vulns} known vulnerability advisory(ies) flagged across {len(PACKAGES)} packages.")
    print("=" * 70)

if __name__ == "__main__":
    main()
