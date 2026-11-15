<?php
declare(strict_types=1);

final class Ledger
{
    public function __construct(private PDO $pdo)
    {
        $this->pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
        $this->pdo->setAttribute(PDO::ATTR_EMULATE_PREPARES, false);
    }

    /** Reserve one request unit atomically and refuse reused idempotency keys. */
    public function reserve(string $tokenHash, string $idempotencyKey, string $requestId): int
    {
        $this->pdo->beginTransaction();
        try {
            $key = $this->pdo->prepare(
                'SELECT k.tenant_id FROM api_keys k JOIN tenants t ON t.id=k.tenant_id ' .
                'WHERE k.key_hash=:key_hash AND k.revoked_at IS NULL AND t.active=1 LIMIT 1'
            );
            $key->execute(['key_hash' => $tokenHash]);
            $row = $key->fetch(PDO::FETCH_ASSOC);
            if (!$row) {
                throw new DomainException('unauthorized');
            }
            $tenantId = (int)$row['tenant_id'];
            $insert = $this->pdo->prepare(
                'INSERT INTO requests (request_id, tenant_id, idem_hash, status, reserved_units) ' .
                "VALUES (:request_id, :tenant_id, :idem_hash, 'reserved', 1)"
            );
            $insert->execute([
                'request_id' => $requestId,
                'tenant_id' => $tenantId,
                'idem_hash' => hash('sha256', $idempotencyKey),
            ]);
            $charge = $this->pdo->prepare(
                'UPDATE tenants SET remaining_units=remaining_units-1 ' .
                'WHERE id=:tenant_id AND active=1 AND remaining_units>=1'
            );
            $charge->execute(['tenant_id' => $tenantId]);
            if ($charge->rowCount() !== 1) {
                throw new DomainException('quota_exceeded');
            }
            $this->pdo->commit();
            return $tenantId;
        } catch (Throwable $e) {
            if ($this->pdo->inTransaction()) {
                $this->pdo->rollBack();
            }
            throw $e;
        }
    }

    /** Settle at most once; no prompt or generated content is written to SQL. */
    public function settle(string $requestId, bool $success, int $latencyMs): void
    {
        $this->pdo->beginTransaction();
        try {
            $select = $this->pdo->prepare(
                'SELECT tenant_id, status, reserved_units FROM requests ' .
                'WHERE request_id=:request_id FOR UPDATE'
            );
            $select->execute(['request_id' => $requestId]);
            $row = $select->fetch(PDO::FETCH_ASSOC);
            if (!$row || $row['status'] !== 'reserved') {
                throw new DomainException('not_reservable');
            }
            $status = $success ? 'succeeded' : 'failed';
            $stmt = $this->pdo->prepare(
                'UPDATE requests SET status=:status, latency_ms=:latency_ms, completed_at=UTC_TIMESTAMP() ' .
                'WHERE request_id=:request_id'
            );
            $stmt->execute(['status' => $status, 'latency_ms' => $latencyMs, 'request_id' => $requestId]);
            if (!$success) {
                $refund = $this->pdo->prepare(
                    'UPDATE tenants SET remaining_units=remaining_units+:units WHERE id=:tenant_id'
                );
                $refund->execute(['units' => (int)$row['reserved_units'], 'tenant_id' => (int)$row['tenant_id']]);
            }
            $this->pdo->commit();
        } catch (Throwable $e) {
            if ($this->pdo->inTransaction()) {
                $this->pdo->rollBack();
            }
            throw $e;
        }
    }
}
