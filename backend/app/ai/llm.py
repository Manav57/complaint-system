"""Groq LLM client wrapper with deterministic mock fallback.

If GROQ_API_KEY is not set, a rule-based mock simulates the LLM so the
full app (LangGraph graph, endpoints, UI) can be exercised end-to-end.
The mock is clearly marked and logs a warning.
"""
import json
import logging
import re
from functools import lru_cache

from app.config import get_settings

logger = logging.getLogger("groq")

settings = get_settings()

_GROQ_IMPORT_ERROR = None
try:
    from langchain_groq import ChatGroq
except Exception as e:  # pragma: no cover
    _GROQ_IMPORT_ERROR = e
    ChatGroq = None


def _load_client(model: str):
    if not settings.groq_configured:
        return None
    if ChatGroq is None:
        logger.error("langchain-groq not installed: %s", _GROQ_IMPORT_ERROR)
        return None
    return ChatGroq(api_key=settings.groq_api_key, model=model, temperature=0.2)


@lru_cache(maxsize=4)
def _default_client():
    return _load_client(settings.groq_model)


@lru_cache(maxsize=4)
def _heavy_client():
    return _load_client(settings.groq_heavy_model)


def llm_call(system_prompt: str, user_prompt: str, *, heavy: bool = False, max_tokens: int = 1500) -> str:
    """Call Groq (gemma2-9b-it by default). Returns deterministic mock text if no key."""
    if not settings.groq_configured:
        logger.warning("GROQ_API_KEY not set - using rule-based MOCK LLM (not real Groq).")
        return _mock_llm(system_prompt, user_prompt)
    client = _heavy_client() if heavy else _default_client()
    if client is None:
        logger.warning("Groq client unavailable - using rule-based MOCK LLM.")
        return _mock_llm(system_prompt, user_prompt)
    try:
        msg = client.invoke([("system", system_prompt), ("user", user_prompt)])
        return str(msg.content).strip()
    except Exception as e:
        logger.error("Groq call failed (%s); falling back to MOCK LLM. Error: %s", type(e).__name__, e)
        return _mock_llm(system_prompt, user_prompt)


# --------------------------------------------------------------------------
# Mock LLM (rule-based) — used only when no GROQ_API_KEY is configured.
# --------------------------------------------------------------------------

_PRODUCTS = [
    "Paracetamol",
    "Amoxicillin",
    "Omeprazole",
    "Metformin",
    "Atorvastatin",
    "Azithromycin",
    "Ibuprofen",
    "Ciprofloxacin",
    "Losartan",
    "Pantoprazole",
]
_CATEGORIES = [
    "Product Quality",
    "Packaging",
    "Labeling",
    "Adverse Event",
    "Contamination",
    "Potency",
    "Stability",
    "Dissolution",
    "Delivery / Logistics",
    "Service",
    "Other",
]
_RISK_PATTERNS: list[tuple[re.Pattern, str, float, str]] = [
    (re.compile(r"adverse|hospitaliz|serious|life.?threat|death|emergency", re.I), "Critical", 0.95, "Potential serious adverse event / patient safety signal"),
    (re.compile(r"contamin|foreign|particle|glass|mold|bacteria|microbial|infection", re.I), "High", 0.85, "Possible contamination or foreign matter - product quality hazard"),
    (re.compile(r"swelling|rash|allerg|hives|itch|difficulty breathing", re.I), "High", 0.8, "Possible adverse reaction with patient impact"),
    (re.compile(r"no effect|ineffect|not working|no relief|didn'?t work", re.I), "High", 0.75, "Reported lack of efficacy - potential potency issue"),
    (re.compile(r"wrong label|label.*wrong|incorrect.*label|missing.*label", re.I), "Medium", 0.65, "Labeling discrepancy - potential patient confusion"),
    (re.compile(r"color|colour|smell|odor|taste|appearance|discolor", re.I), "Medium", 0.6, "Appearance / organoleptic deviation"),
    (re.compile(r"packag|bottle|blister|broken|leak|damaged|seal", re.I), "Medium", 0.55, "Packaging integrity issue"),
    (re.compile(r"capsule|tablet|hard|brittle|stuck|empty", re.I), "Medium", 0.5, "Dosage form defect"),
    (re.compile(r"delayed|late|delivery|shipping|shipment|logistics|order", re.I), "Low", 0.35, "Logistics / delivery concern"),
    (re.compile(r"question|query|information|request|how to|usage", re.I), "Low", 0.25, "Informational query"),
]


def _mock_llm(system_prompt: str, user_prompt: str) -> str:
    combined = (system_prompt + " " + user_prompt).lower()
    if "extract structured" in combined or "auto-populate" in combined:
        return _mock_extract(user_prompt)
    if "risk assessor" in combined:
        return _mock_risk(user_prompt)
    if "completeness" in combined or "quality checker" in combined:
        return _mock_completeness(user_prompt)
    if "capa" in combined or "root causes" in combined:
        return _mock_capa(user_prompt)
    if "summary" in combined:
        return _mock_summary(user_prompt)
    return "MOCK: no handler matched."


def _mock_extract(text: str) -> str:
    fields: dict[str, str] = {}
    m = re.search(r"(?i)(?:i'?m|this is|regards)[,\s:]*\s*(dr\.?|mr\.?|mrs\.?|ms\.?)?\s*([a-z][a-z]+(?:\s+[a-z]+){0,2})\b", text)
    if m and "from" not in m.group(2).lower():
        prefix = (m.group(1) or "").capitalize()
        fields["complainant_name"] = f"{prefix} {m.group(2).title()}".strip()
    if not fields.get("complainant_name"):
        m = re.search(r"(?i)dr\.?\s*([a-z][a-z\s]+?)(?: from|\.|,|$)", text)
        if m:
            fields["complainant_name"] = "Dr. " + " ".join(m.group(1).split()).title()
    m = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text)
    if m:
        fields["complainant_email"] = m.group(0)
    m = re.search(r"(?i)(?:from|at)\s+([A-Z][A-Za-z&\s]+?)(?:\.|,|$)", text)
    if m and any(k in m.group(1).lower() for k in ("pharmacy", "labs", "drugs", "pharma", "hospital")):
        fields["complainant_company"] = " ".join(m.group(1).split())
    for p in _PRODUCTS:
        if p.lower() in text.lower():
            fields["product_name"] = p
            break
    m = re.search(r"(?i)batch[\s#]*([A-Za-z0-9\-]+)", text)
    if m:
        fields["batch_lot_number"] = m.group(1).upper()
    m = re.search(r"(?i)lot[\s#]*([A-Za-z0-9\-]+)", text)
    if m and "batch_lot_number" not in fields:
        fields["batch_lot_number"] = m.group(1).upper()
    for c in _CATEGORIES:
        words = c.lower().split()
        if all(w in text.lower() for w in words) and len(words) > 1:
            fields["category"] = c
            break
    if "category" not in fields:
        keywords = {"quality": "Product Quality", "packaging": "Packaging", "label": "Labeling",
                    "adverse": "Adverse Event", "contamin": "Contamination", "potency": "Potency",
                    "stability": "Stability", "dissolution": "Dissolution", "delivery": "Delivery / Logistics",
                    "service": "Service"}
        for k, v in keywords.items():
            if k in text.lower():
                fields["category"] = v
                break
    m = re.search(r"(?i)exp(?:iry)?[\s:]+([0-9]{1,2}[/.-][0-9]{1,2}[/.-][0-9]{2,4})", text)
    if m:
        fields["expiry_date"] = m.group(1)
    m = re.search(r"(?i)(\d+\s*mg|\d+\s*g\b|\d+\s*ml\b)", text)
    if m:
        fields["strength"] = m.group(1)
    m = re.search(r"(?i)(tablet|capsule|syrup|injection|ointment|suspension|vial|ampoule)", text)
    if m:
        fields["dosage_form"] = m.group(1).lower()
    m = re.search(r"(?i)quantity[\s:]+([0-9]+)", text)
    if m:
        fields["quantity_affected"] = m.group(1)
    if "contamin" in text.lower() or "adverse" in text.lower():
        fields["severity"] = "High"
    elif "delivery" in text.lower() or "late" in text.lower():
        fields["severity"] = "Low"
    else:
        fields["severity"] = "Medium"
    return json.dumps(fields)


def _mock_risk(text: str) -> str:
    for pat, level, score, reason in _RISK_PATTERNS:
        if pat.search(text):
            return json.dumps({
                "risk_level": level, "risk_score": round(score, 2),
                "rationale": reason,
                "category": _pick_category(text),
                "severity": _pick_severity(text, level),
                "mock": True,
            })
    return json.dumps({
        "risk_level": "Low", "risk_score": 0.2,
        "rationale": "No high-risk signals detected in the complaint description.",
        "category": _pick_category(text),
        "severity": "Low",
        "mock": True,
    })


def _pick_category(text: str) -> str:
    for c in _CATEGORIES:
        words = c.lower().split()
        if all(w in text.lower() for w in words) and len(words) > 1:
            return c
    return "Other"


def _pick_severity(text: str, risk: str) -> str:
    if risk in ("Critical", "High"):
        return "High"
    return "Medium"


def _mock_completeness(text: str) -> str:
    missing = []
    if "complainant" not in text.lower() and "name" not in text.lower():
        missing.append("complainant_name")
    if "batch" not in text.lower() and "lot" not in text.lower():
        missing.append("batch_lot_number")
    if "product" not in text.lower():
        missing.append("product_name")
    return json.dumps({"complete": not missing, "missing_fields": missing})


def _mock_summary(text: str) -> str:
    snippet = text[:140].strip()
    return f"Summary: Customer reports {snippet}... (MOCK generated summary)."


def _mock_capa(text: str) -> str:
    return json.dumps({
        "root_cause": "Likely causes: incoming material variance, process deviation, or packaging line fault - verify with batch record review.",
        "capa": "1) Initiate deviation investigation. 2) Review batch record + retention samples. 3) Perform root cause analysis (5-Why / Ishikawa). 4) Implement corrective actions and verify effectiveness. 5) Extend monitoring to adjacent batches.",
    })


def extract_json(response: str) -> dict | None:
    """Robustly parse a JSON object out of an LLM response."""
    if response is None:
        return None
    text = response.strip()
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{.*\}", text, re.S)
    if m:
        try:
            data = json.loads(m.group(0))
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            pass
    return None
