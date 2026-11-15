<?php
declare(strict_types=1);
// Run only after max inference timeout + queue tolerance; use 10 minutes here.
$config = require '/etc/local-ai/gateway-admin.php';
$pdo = new PDO($config['dsn'], $config['db_user'], $config['db_password'], [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);
$pdo->exec("SET time_zone = '+00:00'");
$pdo->setAttribute(PDO::ATTR_EMULATE_PREPARES, false);
$pdo->beginTransaction();
try {
    $rows = $pdo->query(
        "SELECT request_id, tenant_id, reserved_units FROM requests " .
        "WHERE status='reserved' AND created_at < (UTC_TIMESTAMP() - INTERVAL 10 MINUTE) " .
        "ORDER BY created_at ASC LIMIT 100 FOR UPDATE"
    )->fetchAll(PDO::FETCH_ASSOC);
    $expire = $pdo->prepare("UPDATE requests SET status='expired', completed_at=UTC_TIMESTAMP() WHERE request_id=? AND status='reserved'");
    $refund = $pdo->prepare('UPDATE tenants SET remaining_units=remaining_units+? WHERE id=?');
    foreach ($rows as $row) {
        $expire->execute([$row['request_id']]);
        if ($expire->rowCount() === 1) $refund->execute([(int)$row['reserved_units'], (int)$row['tenant_id']]);
    }
    $pdo->commit();
    fwrite(STDOUT, 'Expired: ' . count($rows) . "\n");
} catch (Throwable $e) {
    if ($pdo->inTransaction()) $pdo->rollBack();
    fwrite(STDERR, "Expiration failed\n");
    exit(1);
}
