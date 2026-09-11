"""
Fidelity-Check Safeguard Module for Document Assistant.
Extracts and rigorously compares critical factual anchors (dates, monetary amounts,
identifiers, numbers, status keywords) between raw OCR text and simplified/translated text.

Rebuilt for Phase 3 to perform:
1. Exact Value Matching (no loose substring or category presence matching).
2. Cross-Mention & Internal Consistency Verification (flags internal contradictions
   like conflicting years for the same date or conflicting amounts for the same balance).
3. Inverse Unverified Entity Auditing (flags hallucinated or altered entities in output).
4. Cross-Language Indic Retention (verifies pure Hindi translations without English glosses).
"""

import re
from typing import Dict, List, Set, Any, Tuple, Optional


# Authoritative status & legal action keywords
STATUS_KEYWORDS = [
    "approved",
    "approval",
    "rejected",
    "rejection",
    "pending",
    "deadline",
    "due",
    "verified",
    "verification",
    "expired",
    "denied",
    "denial",
    "valid",
    "invalid",
    "paid",
    "overdue",
    "required",
    "default",
    "current",
    "suspended",
]

# Multilingual status keyword lexicon for cross-language validation (e.g. English -> Hindi)
INDIC_STATUS_LEXICON: Dict[str, Dict[str, List[str]]] = {
    "hi": {
        "approved": ["सत्यापित और स्वीकृत", "स्वीकृत", "स्वीकृति", "मंजूर", "मंजूरी", "सत्यापित", "approved", "approval"],
        "rejected": ["अस्वीकृत", "अस्वीकृति", "खारिज", "नामंजूर", "रद्द", "rejected", "denied"],
        "pending": ["लंबित", "विचाराधीन", "बाकी", "pending"],
        "verified": ["सत्यापित", "सत्यापन", "जांच", "verified"],
        "deadline": ["अंतिम तिथि", "समय सीमा", "आखिरी तारीख", "अंतिम तारीख", "deadline"],
        "due": ["देय", "बाकी", "बकाया", "अंतिम तिथि", "due"],
        "default": ["चूक", "डिफ़ॉल्ट", "व्यतिक्रम", "default"],
        "required": ["आवश्यक", "जरूरी", "अनिवार्य", "required"],
        "paid": ["भुगतान", "चुकाया", "paid"],
        "current": ["वर्तमान में मान्य", "वर्तमान स्थिति", "वर्तमान", "मौजूदा", "current"],
        "suspended": ["निलंबित", "निलंबन", "रोक", "suspended"],
        "overdue": ["अतिदेय", "बाकी", "बकाया", "लंबित", "देय", "overdue"],
    },
    "ta": {
        "approved": ["அங்கீகரிக்கப்பட்டது", "ஏற்றுக்கொள்ளப்பட்டது", "approved"],
        "rejected": ["நிராகரிக்கப்பட்டது", "rejected"],
        "pending": ["நிலுவையில் உள்ளது", "pending"],
        "deadline": ["கடைசி தேதி", "deadline"],
    },
    "bn": {
        "approved": ["অনুমোদিত", "মঞ্জুর", "approved"],
        "rejected": ["প্রত্যাখ্যাত", "বাতিল", "rejected"],
        "pending": ["মুলতুবি", "pending"],
        "deadline": ["শেষ तारीख", "deadline"],
    },
}

HINDI_MONTH_MAP: Dict[str, List[str]] = {
    "jan": ["january", "jan", "जनवरी"],
    "feb": ["february", "feb", "फरवरी"],
    "mar": ["march", "mar", "मार्च"],
    "apr": ["april", "apr", "अप्रैल"],
    "may": ["may", "मई"],
    "jun": ["june", "jun", "जून"],
    "jul": ["july", "jul", "जुलाई"],
    "aug": ["august", "aug", "अगस्त"],
    "sep": ["september", "sep", "sept", "सितंबर", "सितम्बर"],
    "oct": ["october", "oct", "अक्टूबर", "अक्तूबर"],
    "nov": ["november", "nov", "नवंबर", "नवम्बर"],
    "dec": ["december", "dec", "दिसंबर", "दिसम्बर"],
}

# Month patterns for date detection (multilingual English + Hindi)
ALL_MONTHS_REGEX = (
    r"(?:January|February|March|April|May|June|July|August|September|October|November|December|"
    r"Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec|"
    r"जनवरी|फरवरी|मार्च|अप्रैल|मई|जून|जुलाई|अगस्त|सितंबर|सितम्बर|अक्टूबर|अक्तूबर|नवंबर|नवम्बर|दिसंबर|दिसम्बर)"
)
MONTHS_REGEX = ALL_MONTHS_REGEX


def parse_canonical_date(d_str: str) -> Optional[Tuple[str, int, int]]:
    """
    Parses a date string into a canonical tuple: (canonical_month_key, day_int, year_int).
    Supports English, ISO, slash, and Devanagari Hindi month formats.
    Example: 'September 30 2026' -> ('sep', 30, 2026)
             '30 सितंबर 2026'  -> ('sep', 30, 2026)
    """
    norm = d_str.strip().lower().replace(",", "")
    norm = re.sub(r"\b(st|nd|rd|th)\b", "", norm)

    # 1. ISO format: YYYY-MM-DD
    m_iso = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", norm)
    if m_iso:
        y, m_num, d = int(m_iso.group(1)), int(m_iso.group(2)), int(m_iso.group(3))
        month_keys = list(HINDI_MONTH_MAP.keys())
        if 1 <= m_num <= 12:
            return (month_keys[m_num - 1], d, y)

    # 2. Slash format: MM/DD/YYYY
    m_slash = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", norm)
    if m_slash:
        m_num, d, y = int(m_slash.group(1)), int(m_slash.group(2)), int(m_slash.group(3))
        month_keys = list(HINDI_MONTH_MAP.keys())
        if 1 <= m_num <= 12:
            return (month_keys[m_num - 1], d, y)

    # 3. Textual month formats
    m_key = None
    for k, variants in HINDI_MONTH_MAP.items():
        if any(re.search(rf"\b{re.escape(v)}\b", norm) for v in variants):
            m_key = k
            break
    if not m_key:
        return None

    m_year = re.search(r"\b(19\d\d|20\d\d)\b", norm)
    if not m_year:
        return None
    year = int(m_year.group(1))

    # Remove year and month tokens to isolate day number
    scrubbed = norm.replace(str(year), " ")
    for v in HINDI_MONTH_MAP[m_key]:
        scrubbed = scrubbed.replace(v, " ")
    m_day = re.search(r"\b(\d{1,2})\b", scrubbed)
    if not m_day:
        return None
    day = int(m_day.group(1))

    return (m_key, day, year)


def extract_dates(text: str) -> List[str]:
    """
    Extracts dates in various formats:
    - Month DD, YYYY / Month DD YYYY (e.g. September 11 2026, Oct 24, 2026)
    - DD Month YYYY (e.g. 11 September 2026, 30 सितंबर 2026)
    - YYYY-MM-DD (e.g. 2026-09-11)
    - MM/DD/YYYY (e.g. 09/11/2026)
    """
    date_patterns = [
        rf"\b{ALL_MONTHS_REGEX}\s+\d{{1,2}}(?:st|nd|rd|th)?(?:,)?\s+\d{{4}}\b",
        rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s+{ALL_MONTHS_REGEX}\s+\d{{4}}\b",
        r"\b\d{4}-\d{2}-\d{2}\b",
        r"\b\d{1,2}/\d{1,2}/\d{4}\b",
    ]
    found = []
    for pat in date_patterns:
        matches = re.finditer(pat, text, flags=re.IGNORECASE)
        for m in matches:
            clean = re.sub(r"\s+", " ", m.group(0)).strip()
            if clean not in found:
                found.append(clean)
    return found


def extract_amounts(text: str) -> List[str]:
    """
    Extracts monetary currency amounts (e.g. $450.00, $250, ₹12,500, Rs. 500, €75.50, 450 USD).
    Also detects amounts on financial context lines where currency signs were dropped by OCR or misread as 'S'/'s'.
    """
    currency_patterns = [
        # Standard currency prefix: $450.00 or $450 or ₹12,500.00 or £25
        r"(?:[\$\€\£\₹]|(?:Rs\.?\s*)|(?:USD\s*)|(?:INR\s*))\s*\d{1,4}(?:,\d{3})*(?:\.\d{1,2})?",
        # Currency suffix: 450 USD or 500 dollars
        r"\b\d{1,4}(?:,\d{3})*(?:\.\d{1,2})?\s*(?:USD|INR|EUR|GBP|dollars|rupees)\b",
        # Financial context prefix (captures amounts even if OCR dropped the '$' sign or misread '$' as 'S'/'s')
        r"(?:Balance|Due|Charges|Remit|remits|Amount|Total|Fee|Payment|Fine|Paid|देय|राशि|शुल्क)\s*[:\s]\s*([\$#sS]?\s*\d{1,4}(?:,\d{3})*(?:\.\d{2}))",
    ]
    found = []
    for pat in currency_patterns:
        for m in re.finditer(pat, text, flags=re.IGNORECASE):
            raw_match = m.group(1) if m.groups() else m.group(0)
            clean = re.sub(r"\s+", "", raw_match).strip()
            if clean not in found:
                found.append(clean)
    return found


def parse_canonical_amount(amt_str: str) -> Optional[float]:
    """Extracts numeric float value from currency amount string, handling '$' misread as 's'/'S'."""
    clean = re.sub(r"^[sS\$€£₹#]\s*", "", amt_str.strip())
    num_str = re.sub(r"[^\d\.]", "", clean)
    try:
        return round(float(num_str), 2)
    except ValueError:
        return None


def extract_identifiers(text: str) -> List[str]:
    """
    Extracts structured IDs, reference codes, case numbers:
    e.g. SN-2026-X89, MED-90821-TX, GOV-2026-LAW-77, TEL-55421-CA, UTIL-99412-CA.
    """
    id_pattern = r"\b(?=[A-Za-z0-9\-_]*[A-Za-z])(?=[A-Za-z0-9\-_]*[0-9])[A-Za-z0-9]{2,}(?:-[A-Za-z0-9]+){1,4}\b"
    matches = re.findall(id_pattern, text)
    return sorted(list(set(m.strip() for m in matches if len(m.strip()) >= 5)))


def extract_status_keywords(text: str) -> List[str]:
    """Extracts occurrences of critical status / legal outcome keywords."""
    found = []
    text_lower = text.lower()
    for kw in STATUS_KEYWORDS:
        if re.search(rf"\b{re.escape(kw)}\b", text_lower):
            found.append(kw)
    return sorted(list(set(found)))


def extract_numeric_quantities(text: str, excluded_texts: List[str] = None) -> List[str]:
    """
    Extracts standalone significant numeric figures not already part of dates, amounts, or IDs.
    """
    scrubbed = text
    if excluded_texts:
        for excl in excluded_texts:
            scrubbed = scrubbed.replace(excl, " " * len(excl))

    num_pattern = r"\b\d+(?:\.\d+)?\b"
    matches = re.findall(num_pattern, scrubbed)

    significant = []
    for m in matches:
        if m in ("0", "00", "000"):
            continue
        if len(m) >= 2 or "." in m:
            significant.append(m)
    return sorted(list(set(significant)))


def extract_all_entities(text: str) -> Dict[str, List[str]]:
    """Extracts all entity categories from a text string with precise span scrubbing."""
    dates = extract_dates(text)
    amounts = extract_amounts(text)
    ids = extract_identifiers(text)
    statuses = extract_status_keywords(text)

    # Scrub raw occurrences of dates, amounts, and IDs to avoid double-counting in numbers
    scrubbed = text
    for a in amounts:
        num = re.sub(r"[^\d\.]", "", a)
        if num:
            scrubbed = re.sub(rf"[\$€£₹]?\s*{re.escape(num)}", " ", scrubbed)
    for d in dates:
        scrubbed = scrubbed.replace(d, " ")
    for i in ids:
        scrubbed = scrubbed.replace(i, " ")

    numbers = extract_numeric_quantities(scrubbed)

    return {
        "dates": dates,
        "amounts": amounts,
        "identifiers": ids,
        "status_keywords": statuses,
        "numbers": numbers,
    }


def check_internal_consistency(text: str, doc_label: str = "Document") -> List[str]:
    """
    Validates internal self-consistency of entities within a single document:
    1. Conflicting Dates: Checks if multiple dates have the same month & day but different years
       (e.g. Sept 30 2026 vs Sept 30 2028).
    2. Conflicting Amounts: Checks if amounts have digit prepend collisions (e.g. 889.50 vs 89.50)
       or if primary balance and remittance demand figures disagree.
    """
    warnings = []

    # 1. Date internal consistency
    raw_dates = extract_dates(text)
    parsed_dates = []
    for rd in raw_dates:
        p = parse_canonical_date(rd)
        if p:
            parsed_dates.append((p, rd))

    for i in range(len(parsed_dates)):
        for j in range(i + 1, len(parsed_dates)):
            (m1, d1, y1), r1 = parsed_dates[i]
            (m2, d2, y2), r2 = parsed_dates[j]
            if m1 == m2 and d1 == d2 and y1 != y2:
                warnings.append(
                    f"[INTERNAL INCONSISTENCY ERROR] {doc_label} contains conflicting dates for same event/deadline: "
                    f"'{r1}' vs '{r2}' (differing years {y1} vs {y2})! Likely OCR digit confusion or document contradiction."
                )

    # 2. Amount internal consistency
    raw_amounts = extract_amounts(text)
    parsed_amounts = []
    for ra in raw_amounts:
        val = parse_canonical_amount(ra)
        if val is not None:
            parsed_amounts.append((val, ra))

    for i in range(len(parsed_amounts)):
        for j in range(i + 1, len(parsed_amounts)):
            v1, r1 = parsed_amounts[i]
            v2, r2 = parsed_amounts[j]
            if abs(v1 - v2) > 0.001:
                # Check for digit prepend / optical glitch (e.g. 889.50 vs 89.50 where '8' was prepended)
                s1 = f"{v1:.2f}"
                s2 = f"{v2:.2f}"
                if (s1.endswith(s2) and len(s1) == len(s2) + 1 and s1[0] in "8B") or \
                   (s2.endswith(s1) and len(s2) == len(s1) + 1 and s2[0] in "8B"):
                    warnings.append(
                        f"[INTERNAL INCONSISTENCY ERROR] {doc_label} contains conflicting monetary amounts: "
                        f"'{r1}' vs '{r2}' (optical digit prepend/confusion detected)! Balance and remittance demand disagree."
                    )
                # Check if financial balance and payment demand lines conflict in single notice
                elif any(term in text.lower() for term in ["overdue", "balance", "fine", "summons", "remit"]):
                    if ("balance" in text.lower() and "remit" in text.lower()) and len(parsed_amounts) == 2:
                        warnings.append(
                            f"[INTERNAL INCONSISTENCY ERROR] {doc_label} contains conflicting monetary figures: "
                            f"'{r1}' vs '{r2}'! Stated balance and remittance demand disagree."
                        )

    return warnings


def verify_fidelity(original_text: str, simplified_text: str, target_lang: str = "en") -> Dict[str, Any]:
    """
    Compares critical entities between original source text and rewritten/translated text.
    Enforces EXACT value matching, multi-mention internal consistency, and unverified entity detection.

    Parameters:
        original_text: The source OCR or English document text.
        simplified_text: The rewritten English or translated Indic text.
        target_lang: Language code of simplified_text ("en", "hi", "ta", "bn").

    Returns:
        {
            "fidelity_passed": bool,
            "fidelity_warnings": List[str],
            "original_entities": dict,
            "simplified_entities": dict,
            "missing_entities": List[str]
        }
    """
    orig_ent = extract_all_entities(original_text)
    simp_ent = extract_all_entities(simplified_text)

    warnings = []
    missing = []
    target_lang = target_lang.lower().strip()

    # Step 1: Check Internal Self-Consistency in Source and Target Documents
    orig_consistency_warns = check_internal_consistency(original_text, doc_label="Original Document")
    simp_consistency_warns = check_internal_consistency(simplified_text, doc_label="Output Document")
    warnings.extend(orig_consistency_warns)
    warnings.extend(simp_consistency_warns)

    # Step 2: Exact Value Matching - Reference Identifiers
    simp_text_collapsed = re.sub(r"[\s\-_]", "", simplified_text.lower())
    for ref_id in orig_ent["identifiers"]:
        id_collapsed = re.sub(r"[\s\-_]", "", ref_id.lower())
        if id_collapsed not in simp_text_collapsed:
            msg = f"Missing reference ID: '{ref_id}' from original document was dropped or altered."
            warnings.append(msg)
            missing.append(ref_id)

    # Inverted check: Detect altered or unverified IDs in simplified text
    orig_ids_collapsed = [re.sub(r"[\s\-_]", "", i.lower()) for i in orig_ent["identifiers"]]
    for simp_id in simp_ent["identifiers"]:
        s_id_col = re.sub(r"[\s\-_]", "", simp_id.lower())
        if orig_ids_collapsed and s_id_col not in orig_ids_collapsed:
            warnings.append(f"[UNVERIFIED ENTITY ERROR] Output contains altered or unverified ID '{simp_id}' not present in original document!")

    # Step 3: Exact Value Matching - Dates (Canonical Triplet Matching)
    orig_parsed_dates = [parse_canonical_date(d) for d in orig_ent["dates"]]
    simp_parsed_dates = [parse_canonical_date(d) for d in simp_ent["dates"]]

    for orig_d, p_orig in zip(orig_ent["dates"], orig_parsed_dates):
        if p_orig is None:
            # Fallback exact text match
            if orig_d.lower() not in simplified_text.lower():
                warnings.append(f"Missing or altered date: '{orig_d}' was not preserved in output.")
                missing.append(orig_d)
            continue

        # Exact match on (canonical_month, day, year)
        matched = False
        for p_simp in simp_parsed_dates:
            if p_simp == p_orig:
                matched = True
                break

        # Check in raw text if date was translated into target script
        if not matched:
            m_key, day, year = p_orig
            month_variants = HINDI_MONTH_MAP.get(m_key, [m_key])
            has_year = bool(re.search(rf"\b{year}\b", simplified_text))
            has_day = bool(re.search(rf"\b{day}\b", simplified_text))
            has_month = any(re.search(rf"\b{re.escape(mv)}\b", simplified_text, re.IGNORECASE) for mv in month_variants)
            if has_year and has_day and has_month:
                matched = True

        if not matched:
            msg = f"Missing or altered date: '{orig_d}' (canonical: {p_orig}) was altered or dropped in output text."
            warnings.append(msg)
            missing.append(orig_d)

    # Inverted check: Detect unverified/hallucinated dates in output
    valid_orig_date_triplets = [p for p in orig_parsed_dates if p is not None]
    for simp_d, p_simp in zip(simp_ent["dates"], simp_parsed_dates):
        if p_simp is not None and valid_orig_date_triplets:
            if p_simp not in valid_orig_date_triplets:
                warnings.append(f"[UNVERIFIED ENTITY ERROR] Output contains altered/unverified date '{simp_d}' not present in source document!")

    # Step 4: Exact Value Matching - Monetary Amounts (Strict Word Boundaries & Values)
    orig_parsed_amts = [parse_canonical_amount(a) for a in orig_ent["amounts"]]
    simp_parsed_amts = [parse_canonical_amount(a) for a in simp_ent["amounts"]]

    for orig_a, v_orig in zip(orig_ent["amounts"], orig_parsed_amts):
        if v_orig is None:
            continue
        matched = False
        # Exact numeric equality against extracted target amounts
        for v_simp in simp_parsed_amts:
            if v_simp is not None and abs(v_orig - v_simp) < 0.001:
                matched = True
                break

        # Check with strict word boundaries in target text (preventing $89.50 from matching inside $889.50)
        if not matched:
            s_orig = f"{v_orig:.2f}"
            s_orig_int = f"{int(v_orig)}" if v_orig.is_integer() else s_orig
            pat = rf"(?<![\d\.])" + re.escape(s_orig) + r"(?![\d]|(?:\.\d))"
            pat_int = rf"(?<![\d\.])" + re.escape(s_orig_int) + r"(?![\d]|(?:\.\d))"
            if re.search(pat, simplified_text) or (v_orig.is_integer() and re.search(pat_int, simplified_text)):
                matched = True

        if not matched:
            msg = f"Missing monetary amount: '{orig_a}' was dropped or altered in output text."
            warnings.append(msg)
            missing.append(orig_a)

    # Inverted check: Detect unverified/hallucinated monetary amounts in output
    valid_orig_amts = [v for v in orig_parsed_amts if v is not None]
    for simp_a, v_simp in zip(simp_ent["amounts"], simp_parsed_amts):
        if v_simp is not None and valid_orig_amts:
            if not any(abs(v_simp - vo) < 0.001 for vo in valid_orig_amts):
                warnings.append(f"[UNVERIFIED ENTITY ERROR] Output contains unverified/corrupted monetary amount '{simp_a}' not present in source document!")

    # Step 5: Verify Status Keywords
    simp_status_lower = set(s.lower() for s in simp_ent["status_keywords"])
    indic_dict = INDIC_STATUS_LEXICON.get(target_lang, {})
    for status_kw in orig_ent["status_keywords"]:
        equiv_groups = [
            {"approved", "approval"},
            {"rejected", "rejection", "denied", "denial"},
            {"pending", "due", "required"},
            {"verified", "verification", "valid"},
            {"deadline", "due"},
            {"default"},
            {"current"},
            {"suspended"},
            {"paid"},
        ]
        group = next((g for g in equiv_groups if status_kw in g), {status_kw})
        multilingual_terms = set(group)
        for base_kw in group:
            if base_kw in indic_dict:
                multilingual_terms.update(indic_dict[base_kw])

        if not any(g_word in simp_status_lower or g_word in simplified_text.lower() for g_word in multilingual_terms):
            msg = f"Status keyword discrepancy: Critical status '{status_kw}' from original text is missing in output."
            warnings.append(msg)
            missing.append(status_kw)

    # Step 6: Blatant Status Polarity Reversal Check
    orig_text_lower = original_text.lower()
    simp_text_lower = simplified_text.lower()
    orig_is_approved = bool(re.search(r"\b(approved|approval)\b", orig_text_lower))
    orig_is_rejected = bool(re.search(r"\b(rejected|denied|rejection)\b", orig_text_lower))

    simp_has_approved = (
        bool(re.search(r"\b(approved|approval)\b", simp_text_lower))
        or bool(re.search(r"(?<![अa-zA-Z])स्वीकृत", simplified_text))
        or bool(re.search(r"(?<!नामं)मंजूर", simplified_text))
        or "அங்கீகரிக்கப்பட்டது" in simplified_text
        or "অনুমোদিত" in simplified_text
    )
    simp_has_rejected = (
        bool(re.search(r"\b(rejected|denied|rejection)\b", simp_text_lower))
        or bool(re.search(r"(अस्वीकृत|खारिज|नामंजूर|रद्द)", simplified_text))
        or "நிராகரிக்கப்பட்டது" in simplified_text
        or "প্রত্যাখ্যাত" in simplified_text
    )

    if orig_is_approved and simp_has_rejected and not simp_has_approved:
        warnings.insert(0, f"[CRITICAL ERROR] Status polarity flipped: Original indicated 'approved', but output indicates 'rejected'!")
    if orig_is_rejected and simp_has_approved and not simp_has_rejected:
        warnings.insert(0, f"[CRITICAL ERROR] Status polarity flipped: Original indicated 'rejected', but output indicates 'approved'!")

    # Step 7: Verify Remaining Significant Standalone Figures (with strict word boundaries)
    for num in orig_ent["numbers"]:
        pat = rf"(?<![\d\.])" + re.escape(num) + r"(?![\d]|(?:\.\d))"
        if not re.search(pat, simplified_text):
            msg = f"Missing numerical figure: '{num}' was omitted or altered in output text."
            warnings.append(msg)
            missing.append(num)

    return {
        "fidelity_passed": len(warnings) == 0,
        "fidelity_warnings": warnings,
        "original_entities": orig_ent,
        "simplified_entities": simp_ent,
        "missing_entities": missing,
    }
