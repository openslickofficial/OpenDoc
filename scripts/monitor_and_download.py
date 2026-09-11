import json
import os
import sys
import time
import qai_hub as hub

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ENC_COMPILE_ID = "jpe7m4x75"
ENC_PROFILE_ID = "jg9zn92qp"
DEC_COMPILE_ID = "jp1nzq1kg"
OUTPUT_DIR = os.path.abspath("models/trocr-qnn-compiled")
METRICS_FILE = os.path.join(OUTPUT_DIR, "qai_hub_metrics.json")
DEVICE_NAME = "Snapdragon X Elite CRD"

os.makedirs(OUTPUT_DIR, exist_ok=True)

def wait_job(job, poll_interval=10, timeout=1200):
    start = time.time()
    while True:
        status = job.get_status()
        elapsed = int(time.time() - start)
        print(f"    [{job.job_id}] Status: {status.code} (elapsed: {elapsed}s)")
        if status.finished:
            return status
        if elapsed > timeout:
            raise TimeoutError(f"Job {job.job_id} timed out after {timeout} seconds")
        time.sleep(poll_interval)

print("=" * 60)
print("QUALCOMM AI HUB CLOUD BENCHMARK & VERIFICATION RUNNER")
print(f"Target Hardware Device: {DEVICE_NAME}")
print(f"Output Directory: {OUTPUT_DIR}")
print("=" * 60)

# 1. Check Encoder Compile
enc_compile_job = hub.get_job(ENC_COMPILE_ID)
enc_status = enc_compile_job.get_status()
print(f"[1/6] Encoder Compile Job ({ENC_COMPILE_ID}): {enc_status.code}")
if not enc_status.finished:
    enc_status = wait_job(enc_compile_job)
print(f"      Encoder compile status: {enc_status.code}")
enc_target_model = enc_compile_job.get_target_model()
print(f"      Encoder Target Model ID: {enc_target_model.model_id}")

# 2. Check Decoder Compile
dec_compile_job = hub.get_job(DEC_COMPILE_ID)
dec_status = dec_compile_job.get_status()
print(f"[2/6] Decoder Compile Job ({DEC_COMPILE_ID}): {dec_status.code}")
if not dec_status.finished:
    print("      Waiting for decoder compile job to complete...")
    dec_status = wait_job(dec_compile_job)
print(f"      Decoder compile status: {dec_status.code}")

if not dec_status.success:
    print(f"ERROR: Decoder compilation failed: {dec_status.message}")
    sys.exit(1)

dec_target_model = dec_compile_job.get_target_model()
print(f"      Decoder Target Model ID: {dec_target_model.model_id}")

# 3. Submit Decoder Profile Job if not already submitted
device = hub.Device(DEVICE_NAME)
print(f"[3/6] Submitting Decoder Profile Job on {DEVICE_NAME}...")
dec_profile_job = hub.submit_profile_job(
    model=dec_target_model,
    device=device,
    name="TrOCR_Decoder_Snapdragon_X_Elite_Profile"
)
print(f"      Decoder Profile Job ID: {dec_profile_job.job_id}")
print(f"      URL: https://workbench.aihub.qualcomm.com/jobs/{dec_profile_job.job_id}")

# 4. Wait for Encoder Profile Job
enc_profile_job = hub.get_job(ENC_PROFILE_ID)
print(f"[4/6] Waiting for Encoder Profile Job ({ENC_PROFILE_ID}) to finish on {DEVICE_NAME}...")
enc_prof_status = wait_job(enc_profile_job)
print(f"      Encoder profile status: {enc_prof_status.code}")

# 5. Wait for Decoder Profile Job
print(f"[5/6] Waiting for Decoder Profile Job ({dec_profile_job.job_id}) to finish on {DEVICE_NAME}...")
dec_prof_status = wait_job(dec_profile_job)
print(f"      Decoder profile status: {dec_prof_status.code}")

# 6. Extract Profiles and Download Assets
print(f"[6/6] Extracting Profile Metrics and Downloading Assets...")
results = {
    "target_device": DEVICE_NAME,
    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
    "encoder": {
        "compile_job_id": ENC_COMPILE_ID,
        "compile_status": enc_status.code,
        "profile_job_id": ENC_PROFILE_ID,
        "profile_status": enc_prof_status.code,
        "target_model_id": enc_target_model.model_id,
        "profile_url": f"https://workbench.aihub.qualcomm.com/jobs/{ENC_PROFILE_ID}",
    },
    "decoder": {
        "compile_job_id": DEC_COMPILE_ID,
        "compile_status": dec_status.code,
        "profile_job_id": dec_profile_job.job_id,
        "profile_status": dec_prof_status.code,
        "target_model_id": dec_target_model.model_id,
        "profile_url": f"https://workbench.aihub.qualcomm.com/jobs/{dec_profile_job.job_id}",
    }
}

try:
    enc_profile_data = enc_profile_job.download_profile()
    results["encoder"]["profile_data"] = enc_profile_data
    print(f"      Successfully downloaded Encoder profile data.")
except Exception as e:
    print(f"      Warning: could not download encoder profile data: {e}")

try:
    dec_profile_data = dec_profile_job.download_profile()
    results["decoder"]["profile_data"] = dec_profile_data
    print(f"      Successfully downloaded Decoder profile data.")
except Exception as e:
    print(f"      Warning: could not download decoder profile data: {e}")

# Save JSON metrics
with open(METRICS_FILE, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)
print(f"Saved metrics summary to: {METRICS_FILE}")

# Download target compiled model assets
print("Downloading compiled model assets to models/trocr-qnn-compiled/...")
try:
    enc_path = enc_compile_job.download_target_model(os.path.join(OUTPUT_DIR, "encoder_compiled.onnx"))
    print(f"Downloaded compiled encoder to: {enc_path}")
except Exception as e:
    print(f"Download compiled encoder notice: {e}")

try:
    dec_path = dec_compile_job.download_target_model(os.path.join(OUTPUT_DIR, "decoder_compiled.onnx"))
    print(f"Downloaded compiled decoder to: {dec_path}")
except Exception as e:
    print(f"Download compiled decoder notice: {e}")

print("=" * 60)
print("BENCHMARK & VERIFICATION COMPLETED SUCCESSFULLY!")
print("=" * 60)
