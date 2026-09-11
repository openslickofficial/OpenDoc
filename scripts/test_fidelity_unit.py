import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.fidelity_checker import verify_fidelity, extract_all_entities

orig = "Fine of $250.00 is due on November 15 2026 under Case GOV-2026-LAW-77. Status: pending."
print("Entities in orig:", extract_all_entities(orig))

# Case 3: Missing amount ($250 dropped)
simp3 = "You have a fine due on November 15 2026 under Case GOV-2026-LAW-77. Status: pending."
res3 = verify_fidelity(orig, simp3)
print("Case 3 (dropped amount) warnings:", res3["fidelity_warnings"])

# Case 4: Missing ID (GOV-2026-LAW-77 dropped)
simp4 = "You have a fine of $250.00 due on November 15 2026. Status: pending."
res4 = verify_fidelity(orig, simp4)
print("Case 4 (dropped ID) warnings:", res4["fidelity_warnings"])

# Case 5: All preserved
simp5 = "A fine of $250 is due on November 15, 2026 for case GOV-2026-LAW-77. Status is pending."
res5 = verify_fidelity(orig, simp5)
print("Case 5 (all preserved) passed:", res5["fidelity_passed"], "warnings:", res5["fidelity_warnings"])

# Case 6: Cross-Language Hindi Translation (All preserved)
hindi_valid = "मामला GOV-2026-LAW-77 के तहत November 15, 2026 को $250.00 का जुर्माना देय (due) है। स्थिति: लंबित (pending)।"
res6 = verify_fidelity(orig, hindi_valid, target_lang="hi")
print("Case 6 (Hindi all preserved) passed:", res6["fidelity_passed"], "warnings:", res6["fidelity_warnings"])

# Case 7: Cross-Language Polarity Flip (approved -> rejected)
orig_app = "Application SN-2026-X89: Status is APPROVED."
hindi_flipped = "आवेदन SN-2026-X89: स्थिति अस्वीकृत (REJECTED) है।"
res7 = verify_fidelity(orig_app, hindi_flipped, target_lang="hi")
print("Case 7 (Polarity Flip intercepted) passed:", not res7["fidelity_passed"], "warnings:", res7["fidelity_warnings"])

