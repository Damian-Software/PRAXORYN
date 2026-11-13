"""Synthetic examples. No network, model, database or firewall access."""
from datetime import datetime, timedelta, timezone
from slo import calculate_slo
from admission import AdmissionController
from recovery import assess_recovery_point
from release_gate import evaluate_gate

report = calculate_slo(10_000, 9_995, "0.999")
controller = AdmissionController(capacity=2, per_tenant_limit=1)
controller.admit("job-a", "tenant-a")
controller.admit("job-b", "tenant-b")
now = datetime(2026, 11, 13, 12, 0, tzinfo=timezone.utc)
recovery = assess_recovery_point(now, now-timedelta(minutes=15),
                                 timedelta(minutes=10), True)
gate = evaluate_gate({"hash": "pass", "license": "pass",
                      "authorization": "pass", "performance": "not_run"},
                     {"hash", "license", "authorization", "performance"},
                     {"hash", "authorization"})
print({"slo_status": report.status, "available_slots": controller.capacity-len(controller.active),
       "rpo_acceptable": recovery.acceptable, "release_approved": gate.approved})
