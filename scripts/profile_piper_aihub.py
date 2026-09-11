"""
Profile Piper Hindi TTS ONNX model on Snapdragon X Elite CRD via Qualcomm AI Hub.
"""
import os
import sys
import numpy as np
import qai_hub as hub

MODEL_PATH = "models/piper_hi/hi_IN-pratham-medium.onnx"

def main():
    print("Connecting to Qualcomm AI Hub...")
    device = hub.Device("Snapdragon X Elite CRD")
    print(f"Target Device: {device.name}")

    # Prepare sample inputs for profiling: 1 sentence of 50 phoneme IDs
    input_ids = np.ones((1, 50), dtype=np.int64)
    input_lengths = np.array([50], dtype=np.int64)
    scales = np.array([0.667, 1.0, 0.8], dtype=np.float32)

    sample_inputs = {
        "input": input_ids,
        "input_lengths": input_lengths,
        "scales": scales,
    }

    print(f"Uploading model: {MODEL_PATH} ({os.path.getsize(MODEL_PATH)} bytes)...")
    uploaded_model = hub.upload_model(MODEL_PATH)
    print(f"Uploaded model ID: {uploaded_model.model_id}")

    print("Submitting profile job on Snapdragon X Elite CRD...")
    profile_job = hub.submit_profile_job(
        model=uploaded_model,
        device=device,
        name="piper_hi_pratham_profile",
        options="--target_runtime onnx",
    )
    print(f"Submitted profile job ID: {profile_job.job_id}")
    print(f"Job URL: https://workbench.aihub.qualcomm.com/jobs/{profile_job.job_id}")

if __name__ == "__main__":
    main()
