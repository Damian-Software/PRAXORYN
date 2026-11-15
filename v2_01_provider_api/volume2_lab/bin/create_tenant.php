<?php
declare(strict_types=1);

if (PHP_SAPI !== 'cli' || count($argv) !== 3 || !preg_match('/^[a-z0-9-]{3,64}$/D', $argv[1]) || !ctype_digit($argv[2])) {
    fwrite(STDERR, "Usage: php create_tenant.php <slug> <initial_units>\n");
    exit(2);
}
$config = require '/etc/local-ai/gateway-admin.php';
$token = rtrim(strtr(base64_encode(random_bytes(32)), '+/', '-_'), '=');
$pdo = new PDO($config['dsn'], $config['db_user'], $config['db_password'], [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);
$pdo->exec("SET time_zone = '+00:00'");
$pdo->beginTransaction();
try {
    $tenant = $pdo->prepare('INSERT INTO tenants (slug, remaining_units) VALUES (?, ?)');
    $tenant->execute([$argv[1], $argv[2]]);
    $id = (int)$pdo->lastInsertId();
    $key = $pdo->prepare('INSERT INTO api_keys (tenant_id, key_hash) VALUES (?, ?)');
    $key->execute([$id, hash('sha256', $token)]);
    $pdo->commit();
} catch (Throwable $e) {
    if ($pdo->inTransaction()) $pdo->rollBack();
    fwrite(STDERR, "Provisioning failed\n");
    exit(1);
}
fwrite(STDERR, "Store the token in a secret manager; it cannot be recovered.\n");
fwrite(STDOUT, $token . "\n");
