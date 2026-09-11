import sys
import os

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.translate_module import apply_anchor_preservation, translate_text

samples = {
    "form_document": """This is a verification form for Snapdragon X hardware.
Application ID: SN-2026-X89.
Applicant Name: Dr. Arthur Vance.
Verification Date: September 11, 2026.
Device Model: HP OmniBook Snapdragon X.
System used: QNN ExecutionProvider.
Status: VERIFIED AND APPROVED.""",

    "medical_bill": """Metropolitan General Hospital
Patient Billing Statement: Clinical Services.
Patient Name: Harold Jenkins.
Statement Date: October 24, 2026.
Claim Reference ID: MED-90821-TX.
Total Charges: $450.00.
Claim Determination: All inpatient and clinical expenses verified and approved.""",

    "legal_notice": """Notice of Administrative Enforcement.
Case ID: GOV-2026-LAW-77.
Immediate payment of $250.00 required before deadline November 15, 2026.
Failure to comply will result in administrative hearing and penalty escalation.
Current Status: PENDING PAYMENT.""",

    "utility_bill": """Municipal Power & Water Authority
Residential Utility Statement.
Consumer Account Number: ELEC-98234-NY.
Billing Cycle: August 2026.
Meter Reading Units: 420 kWh.
Net Due Amount: $135.50.
Payment Due Date: September 28, 2026.
Account Standing: CURRENT.""",

    "printed_paragraph": """Snapdragon X Elite NPU Acceleration: Technical Brief for the Document Processing System. The Hexagon NPU delivers dedicated tensor acceleration for vision. Executing the TrOCR vision encoder on the Hexagon processor via QNN achieves high energy efficiency without sending data to the cloud. Hardware target: HP OmniBook X running ARM64 Windows 11.""",

    "flowing_prose": """Department of Municipal Revenue and Tax Assessment. Dear Taxpayer, please be advised that our annual audit of your real estate property assessment has concluded. Regarding your property filing under Reference ID TAX-2026-8819, the board of assessors met on October 15, 2026 and confirmed that your annual exemption is verified and approved. An administrative adjustment fee of $320.00 is currently pending and must be submitted before the statutory deadline of November 15, 2026 to avoid penalty escalation."""
}

print("=== TESTING apply_anchor_preservation ===")
for name in ["flowing_prose"]:
    text = samples[name]
    print(f"\n[{name}] Running translation...")
    res = translate_text(text, "hi", engine_mode="cpu")
    print(f"  Provider       : {res['provider_used']}")
    print(f"  Latency        : {res['latency_ms']:.2f} ms")
    print(f"  Fidelity Pass  : {res['fidelity_passed']}")
    print(f"  Warnings       : {res['fidelity_warnings']}")
    print("  Output lines:")
    for l in res['translated_text'].split("\n"):
        print("   ", l)
