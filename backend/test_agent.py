"""Sanity test for the LangGraph + Groq agent paths.

Runs varied pharma complaints through the extract and assess workflows
(uses real Groq if GROQ_API_KEY is set, otherwise the rule-based mock)
and prints a sanity summary.
"""
import json
import sys

sys.path.insert(0, ".")

from app.ai.graph import get_assess_workflow, get_extract_workflow

SAMPLES = [
    {
        "name": "1. Contamination / foreign matter",
        "text": "Customer reports 6 tablets in batch PAR-2024-1187 have black specks on the surface and a strong burnt odor. The tablets were dispensed from a sealed blister pack. Photos provided show dark discoloration covering about 20% of the tablet surface.",
        "expect": {"High", "Critical"},
    },
    {
        "name": "2. Adverse event with ER visit",
        "text": "Patient developed severe skin rash and swelling of the face within 2 hours of taking Omeprazole 20mg from batch OME-2024-2210. Patient visited the emergency room. No known allergies prior to this event.",
        "expect": {"High", "Critical"},
    },
    {
        "name": "3. Delivery / logistics delay",
        "text": "Shipment of Azithromycin suspension arrived 4 days late due to carrier delay. Pharmacy ran out of stock and had to direct patients to a competitor. No product quality issue reported.",
        "expect": {"Low", "Medium"},
    },
    {
        "name": "4. Labeling discrepancy",
        "text": "Cartons of Atorvastatin 10mg from batch ATO-2024-0955 have the strength printed as '100 mg' on the side panel. The blister pack label inside is correct at 10mg. Potential for patient confusion with incorrect dosing.",
        "expect": {"Medium", "Low", "High"},
    },
]

extract_graph = get_extract_workflow()
assess_graph = get_assess_workflow()

print("=" * 78)
print("EXTRACT WORKFLOW (form auto-population)")
print("=" * 78)
for s in SAMPLES:
    state = extract_graph.invoke({"raw_text": s["text"], "description": s["text"]})
    fields = state.get("extracted_fields", {})
    keys = [k for k, v in fields.items() if v]
    print(f"{s['name']}")
    print(f"   extracted fields ({len(keys)}): {', '.join(keys) if keys else 'NONE'}")
    if not keys:
        print("   !! FAIL: no fields extracted")

print()
print("=" * 78)
print("ASSESS WORKFLOW (Copilot risk assessment)")
print("=" * 78)
fails = 0
for s in SAMPLES:
    state = assess_graph.invoke({"description": s["text"], "raw_text": s["text"]})
    r = state.get("result", {})
    level = r.get("risk_level")
    ok = level in s["expect"]
    if not ok:
        fails += 1
    print(f"{s['name']}")
    print(f"   risk={level!r} score={r.get('risk_score')} expected={s['expect']} -> {'OK' if ok else 'FAIL'}")
    print(f"   rationale: {str(r.get('rationale'))[:90]}")
    print(f"   summary: {str(r.get('summary'))[:70]}")
    print(f"   root_cause: {str(r.get('root_cause_suggestion'))[:70]}")
    print(f"   capa: {str(r.get('capa_recommendation'))[:70]}")

print()
print(f"RESULT: {len(SAMPLES) - fails}/{len(SAMPLES)} risk classifications matched expectation")
sys.exit(1 if fails else 0)
