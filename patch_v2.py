# --- 1. prompt v2: three boundary fixes found on DEV
p = "classify.py"; s = open(p).read()
fixes = [
 ("- Payroll: this month's pay run or its output is wrong or failed: run stuck, net pay or deduction wrong, salary not credited, payslip blank or not downloading, payslip vs bank file mismatch, arrears missing, bank/WPS payment file rejected by the bank.",
  "- Payroll: this month's pay run or its output is wrong or failed: run stuck, net pay or deduction wrong, salary not credited, payslip blank or not downloading, payslip vs bank file mismatch, PF/ESI amount on the payslip not matching the ECR or challan, arrears missing, bank/WPS payment file rejected by the bank."),
 ("- Statutory: the rules themselves: PF/ESI/PT/TDS/gratuity rates, ceilings, slabs, applicability, Form 16, regime choice, statutory file formats and their rejection codes, differences against an accountant's computation.",
  "- Statutory: the rules themselves: PF/ESI/PT/TDS/gratuity rates, ceilings, slabs, applicability, Form 16, regime choice, statutory file formats and their rejection codes, statutory accrual reports (e.g. gratuity accrual), differences against an accountant's computation."),
 ("- Reports: report builder, registers and exports, blank reports.",
  "- Reports: report builder, custom reports, registers and exports, blank reports (not statutory accruals)."),
 ("- Leave & Attendance: leave balances, carry forward, attendance regularisation.",
  "- Leave & Attendance: leave balances, carry forward, attendance regularisation, including when approved attendance or leave is not reflecting in payroll (the fix is in the attendance or leave data, so it belongs here, not Payroll)."),
]
for a, b in fixes:
    assert a in s, "prompt line not found: " + a[:40]
    s = s.replace(a, b, 1)
open(p, "w").write(s)
# --- 2. gold set: record Jira escalations separately
p = "labels.py"; s = open(p).read()
a = '            needs_human=any((a == "replied" and md.get("tier") in ("L2", "L3")) or a == "escalated" for a, md in ev)))'
assert a in s, "labels.py line not found"
s = s.replace(a, a[:-2] + ',\n            escalated=any(a == "escalated" for a, md in ev)))', 1)
open(p, "w").write(s)
# --- 3. eval: cache keyed by prompt, hard vs L2-only safety split
p = "eval_routing.py"; s = open(p).read()
a = 'from classify import classify, MODEL'
assert a in s; s = s.replace(a, 'from classify import classify, MODEL, PROMPT\nimport hashlib\nPV = hashlib.md5(PROMPT.encode()).hexdigest()[:6]', 1)
a = 'cache_f = f"eval/cls_cache_{MODEL}.json"'
assert a in s; s = s.replace(a, 'cache_f = f"eval/cls_cache_{MODEL}_{PV}.json"', 1)
a = '''human = [r for r in res if r["needs_human"]]
unsafe = [r for r in human if r["path"] == "answer"]'''
assert a in s; s = s.replace(a, '''HARD = {"Payroll", "Billing", "Integration"}
hard = [r for r in res if r.get("escalated") or r["gold_category"] in HARD]
human = [r for r in res if r["needs_human"]]
unsafe = [r for r in hard if r["path"] == "answer"]
soft = [r for r in human if r["path"] == "answer" and r not in hard]''', 1)
a = '''print(f"needed L2/L3 or Jira: {len(human)} | router sent to auto-answer anyway: {len(unsafe)} ({len(unsafe)/max(1,len(human)):.1%})")'''
assert a in s; s = s.replace(a, '''print(f"prompt: {PV}")
print(f"HARD human cases (Jira, or money/account/defect category): {len(hard)} | auto-answered: {len(unsafe)}  | target: 0")
print(f"L2-only cases (L2 replied, no Jira, self-serve category): {len([r for r in human if r not in hard])} | auto-answered: {len(soft)}  (answer step must still find a valid source)")''', 1)
open(p, "w").write(s)
print("v2 patches applied")
