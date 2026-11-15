# Incident handling

When a service reports a security anomaly, the on-call engineer must verify the alert, preserve relevant telemetry, and open an incident ticket. The AI service may summarize evidence, but it must not automatically delete user accounts or block a subnet without explicit approval under the organization's change policy.

Logs containing secrets must not be copied into tickets. The incident owner records event identifiers, timestamps, affected services, and remediation approval. Rollback plans must be prepared before applying a firewall rule.
