"""Classify a masked ticket with Gemini on Vertex AI."""
import os, time, json
from embed import _project
from typing import Literal
from pydantic import BaseModel

MODEL = os.environ.get("CLASSIFY_MODEL", "gemini-3.5-flash-lite")
# No Gemini model is available in me-central1/me-central2 for this project (probed 18 Nov 2026),
# so UAE tickets are classified in Mumbai after PII masking. Storage stays in the UAE-side database.
LOCATION = {"IN": "asia-south1", "UAE": "asia-south1"}

class Classification(BaseModel):
    category: Literal["Payroll", "Statutory", "How-To", "Reports", "Leave & Attendance", "Integration",
                      "Billing", "Access / Login", "Onboarding"]
    money_impact: bool        # someone's pay, a deduction, a payment or a refund is (or may be) wrong
    suspected_defect: bool    # the product looks broken (blank output, stuck job, duplicate data, error after update)
    language: Literal["en", "hinglish", "hi", "ar", "other"]

PROMPT = """You triage support tickets for an HR and payroll SaaS used in India and the UAE.
Personal identifiers are already masked as [EMAIL], [PAN] and so on.

Pick exactly one category:
- Payroll: this month's pay run or its output is wrong or failed: run stuck, net pay or deduction wrong, salary not credited, payslip blank or not downloading, payslip vs bank file mismatch, PF/ESI amount on the payslip not matching the ECR or challan, arrears missing, bank/WPS payment file rejected by the bank.
- Statutory: the rules themselves: PF/ESI/PT/TDS/gratuity rates, ceilings, slabs, applicability, Form 16, regime choice, statutory file formats and their rejection codes, statutory accrual reports (e.g. gratuity accrual), differences against an accountant's computation.
- How-To: how to do something in the product (add employees, bulk upload, salary components, approvers, permissions, sending or downloading payslips).
- Reports: report builder, custom reports, registers and exports, blank reports (not statutory accruals).
- Leave & Attendance: leave balances, carry forward, attendance regularisation, including when approved attendance or leave is not reflecting in payroll (the fix is in the attendance or leave data, so it belongs here, not Payroll).
- Integration: API, tokens, webhooks, HRIS or biometric sync.
- Billing: Ramco Payce's own invoices to the customer, refunds of fees.
- Access / Login: sign-in, SSO, passwords, admin locked out.
- Onboarding: new customer setup, data migration, go-live.

Also set:
- money_impact: true if any amount may be wrong or is disputed: pay, a deduction or contribution, a figure that differs from another document or from the customer's own computation, a payment or a refund. False for a general question about how a rule works.
- suspected_defect: true if the product seems broken: blank output, a stuck job, duplicate or missing data, an error after an update, a sync or upload failing.

Ticket subject: {subject}
Ticket body: {body}"""

import threading
_clients = {}
_lock = threading.Lock()
def classify(subject, body, region):
    from google import genai
    from google.genai import types
    loc = LOCATION[region]
    with _lock:
        if loc not in _clients:
            _clients[loc] = genai.Client(vertexai=True, project=_project(), location=loc)
    t0 = time.perf_counter()
    for attempt in range(6):
        try:
            r = _clients[loc].models.generate_content(
                model=MODEL, contents=PROMPT.format(subject=subject or "", body=body or ""),
                config=types.GenerateContentConfig(temperature=0, response_mime_type="application/json",
                                                   response_schema=Classification,
                                                   thinking_config=types.ThinkingConfig(thinking_level="MINIMAL")))
            break
        except Exception as e:
            if attempt == 5 or not any(c in str(e) for c in ("429", "503", "RESOURCE_EXHAUSTED")): raise
            time.sleep(2 ** attempt)
    out = json.loads(r.text)
    u = r.usage_metadata
    out["_latency_s"] = round(time.perf_counter() - t0, 3)
    out["_tokens_in"] = u.prompt_token_count or 0
    out["_tokens_out"] = (u.candidates_token_count or 0) + (getattr(u, "thoughts_token_count", 0) or 0)
    return out
