import json
import os
import sys
import time
import qai_hub as hub

ENC_COMPILE_ID = "jpe7m4x75"
ENC_PROFILE_ID = "jg9zn92qp"
DEC_COMPILE_ID = "jp1nzq1kg"
DEC_PROFILE_ID = "j57ervnqp"

DEVICE_NAME = "Snapdragon X Elite CRD"
OUTPUT_DIR = os.path.abspath("models/trocr-qnn-compiled")
METRICS_FILE = os.path.join(OUTPUT_DIR, "qai_hub_metrics.json")

os.makedirs(OUTPUT_DIR, exist_ok=True)

def poll_job(job, job_name, interval=10, max_wait=600):
    start = time.time()
    print(f"[*] Polling {job_name} ({job.job_id})...", flush=True)
    while True:
        status = job.get_status()
        elapsed = int(time.time() - start)
        print(f"    [{job.job_id}] Status: {status.code} ({elapsed}s elapsed)", flush=True)
        if status.finished:
            return status
        if elapsed > max_wait:
            raise TimeoutError(f"{job_name} ({job.job_id}) timed out after {max_wait}s")
        time.sleep(interval)

print("=" * 65)
print(f"QUALCOMM AI HUB PROFILE COLLECTOR - {DEVICE_NAME}")
print("=" * 65, flush=True)

enc_job = hub.get_job(ENC_PROFILE_ID)
enc_status = poll_job(enc_job, "Encoder Profile Job")

dec_job = hub.get_job(DEC_PROFILE_ID)
dec_status = poll_job(dec_job, "Decoder Profile Job")

print("\n" + "=" * 65)
print("EXTRACTING PROFILES & COMPUTING HARDWARE METRICS")
print("=" * 65, flush=True)

enc_prof = {}
dec_prof = {}

try:
    enc_prof = enc_job.download_profile()
    print("[+] Downloaded Encoder profile.")
except Exception as e:
    print(f"[-] Could not download Encoder profile: {e}")

try:
    dec_prof = dec_job.download_profile()
    print("[+] Downloaded Decoder profile.")
except Exception as e:
    print(f"[-] Could not download Decoder profile: {e}")

summary = {
    "device": DEVICE_NAME,
    "target_platform": "Windows 11 ARM64 (Snapdragon X Elite)",
    "timestamp_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
    "encoder": {
        "compile_job_id": ENC_COMPILE_ID,
        "profile_job_id": ENC_PROFILE_ID,
        "profile_status": enc_status.code,
        "compile_url": f"https://workbench.aihub.qualcomm.com/jobs/{ENC_COMPILE_ID}",
        "profile_url": f"https://workbench.aihub.qualcomm.com/jobs/{ENC_PROFILE_ID}",
        "profile_metrics": enc_prof,
    },
    "decoder": {
        "compile_job_id": DEC_COMPILE_ID,
        "profile_job_id": DEC_PROFILE_ID,
        "profile_status": dec_status.code,
        "compile_url": f"https://workbench.aihub.qualcomm.com/jobs/{DEC_COMPILE_ID}",
        "profile_url": f"https://workbench.aihub.qualcomm.com/jobs/{DEC_PROFILE_ID}",
        "profile_metrics": dec_prof,
    }
}

with open(METRICS_FILE, "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2)

print(f"\n[+] Full metrics saved to: {METRICS_FILE}")

def print_metrics(name, data):
    print(f"\n--- {name} Hardware Metrics ---")
    if not isinstance(data, dict):
        print(f"Raw data: {data}")
        return
    execution_summary = data.get("execution_summary", {})
    if execution_summary:
        print(f"Estimated Inference Time: {execution_summary.get('estimated_inference_time')}")
        print(f"Inference Time Range: {execution_summary.get('inference_time')}")
    else:
        # Check other possible top-level keys
        for k in ["inference_time", "execution_detail", "compute_unit_counts", "memory_metrics"]:
            if k in data:
                print(f"{k}: {data[k]}")

print_metrics("Encoder (Vision Backbone)", enc_prof)
print_metrics("Decoder (Autoregressive LM)", dec_prof)
print("\n" + "=" * 65)
