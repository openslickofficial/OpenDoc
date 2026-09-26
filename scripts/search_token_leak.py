import configparser
import os
import subprocess

p = os.path.expanduser("~/.qai_hub/client.ini")
cfg = configparser.ConfigParser()
cfg.read(p)
tok = cfg.get("api", "api_token", fallback="").strip()

if not tok:
    print("No token found in client.ini")
    exit(0)

print(f"Token identified (length: {len(tok)}, prefix: {tok[:6]}, suffix: {tok[-4:]})", flush=True)

# 1. Search git commit messages and diffs
print("\n[1] Searching git commit log & diff history...", flush=True)
res = subprocess.run(["git", "--no-pager", "log", "-p", f"-S{tok}"], capture_output=True, text=True)
if res.stdout.strip():
    print("ALERT: Token found in git log history!", flush=True)
    print(res.stdout[:500], flush=True)
else:
    print("PASS: Token NOT found in any git commit or diff.", flush=True)

# 2. Search git commit messages for token prefix
res_prefix = subprocess.run(["git", "--no-pager", "log", "--all", "--grep", tok[:8]], capture_output=True, text=True)
if res_prefix.stdout.strip():
    print(f"ALERT: Token prefix found in git commit messages: {res_prefix.stdout}", flush=True)
else:
    print("PASS: Token prefix NOT found in git commit messages.", flush=True)

# 3. Check PowerShell history file
ps_history_path = os.path.expanduser(r"~\AppData\Roaming\Microsoft\Windows\PowerShell\PSReadLine\ConsoleHost_history.txt")
print(f"\n[2] Checking PowerShell command history: {ps_history_path}")
if os.path.exists(ps_history_path):
    with open(ps_history_path, "r", encoding="utf-8", errors="ignore") as f:
        ps_lines = f.readlines()
    matching_ps = [l.strip() for l in ps_lines if tok in l or tok[:10] in l]
    if matching_ps:
        print(f"ALERT: Found token in PowerShell history ({len(matching_ps)} lines):")
        for m in matching_ps:
            print("  ", m[:60] + "...")
    else:
        print("PASS: Token NOT found in PowerShell history.")
else:
    print("PowerShell history file does not exist.")

# 4. Search all text/config/code/doc files in doc-assistant (skipping giant model weights and dist binaries)
print("\n[3] Searching workspace files for token...")
found_files = []
skip_exts = {".onnx", ".data", ".bin", ".pt", ".safetensors", ".exe", ".dll", ".pyd", ".png", ".jpg", ".wav", ".mp3", ".pack", ".idx"}
skip_dirs = {"dist", "build", ".venv", ".git"}

for root, dirs, files in os.walk("."):
    dirs[:] = [d for d in dirs if d not in skip_dirs]
    for f in files:
        ext = os.path.splitext(f)[1].lower()
        if ext in skip_exts:
            continue
        fp = os.path.join(root, f)
        try:
            with open(fp, "r", encoding="utf-8", errors="ignore") as fl:
                content = fl.read()
                if tok in content or tok[:12] in content:
                    found_files.append(fp)
        except Exception:
            pass

if found_files:
    print("ALERT: Token found in workspace files:", found_files)
else:
    print("PASS: Clean! Token NOT found in any workspace source, config, documentation, or log files.")
