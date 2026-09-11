import json
import collections

with open("models/trocr-qnn-compiled/qai_hub_metrics.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print("=" * 70)
print("SNAPDRAGON X ELITE HARDWARE VERIFICATION SUMMARY")
print(f"Target Device  : {data.get('device')}")
print(f"Target Platform: {data.get('target_platform')}")
print(f"Timestamp (UTC): {data.get('timestamp_utc')}")
print("=" * 70)

for comp in ["encoder", "decoder"]:
    info = data[comp]
    pdata = info.get("profile_metrics", {})
    summary = pdata.get("execution_summary", {})
    detail = pdata.get("execution_detail", [])
    
    compute_units = collections.Counter(item.get("compute_unit", "UNKNOWN") for item in detail)
    time_by_unit = collections.defaultdict(int)
    for item in detail:
        time_by_unit[item.get("compute_unit", "UNKNOWN")] += item.get("execution_time", 0)
    
    total_time = sum(time_by_unit.values())
    npu_pct = (time_by_unit.get("NPU", 0) / total_time * 100) if total_time else 0.0
    
    print(f"\n[+] {comp.upper()} ({'Vision Backbone' if comp == 'encoder' else 'Autoregressive LM'}):")
    print(f"    * Compile Job ID : {info['compile_job_id']}")
    print(f"    * Profile Job ID : {info['profile_job_id']}")
    print(f"    * Compile URL    : {info['compile_url']}")
    print(f"    * Profile URL    : {info['profile_url']}")
    print(f"    * Latency        : {summary.get('estimated_inference_time', 0) / 1000.0:.2f} ms")
    print(f"    * Peak Memory    : {summary.get('estimated_inference_peak_memory', 0) / (1024*1024):.2f} MB")
    print(f"    * Total Layers   : {len(detail)}")
    print(f"    * Layer Plcmnt   : {dict(compute_units)}")
    print(f"    * NPU Compute %  : {npu_pct:.1f}%")
print("=" * 70)
