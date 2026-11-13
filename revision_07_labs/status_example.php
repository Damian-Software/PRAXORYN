<?php
// Demonstration only. Assume authentication middleware has already established identity.
declare(strict_types=1);
session_start([
    'cookie_httponly' => true,
    'cookie_secure' => true,
    'cookie_samesite' => 'Strict',
    'use_strict_mode' => true,
]);
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

$tenantId = $_SESSION['tenant_id'] ?? null;
$jobUuid = $_GET['job_id'] ?? '';
if (!is_string($tenantId) || $tenantId === '' || !is_string($jobUuid)
    || !preg_match('/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/iD', $jobUuid)) {
    http_response_code(403);
    echo json_encode(['error' => 'not_authorized']);
    exit;
}

// No password or DSN in source code or logs; use a managed environment secret.
$dsn = getenv('AI_DB_DSN');
$user = getenv('AI_DB_USER');
$password = getenv('AI_DB_PASSWORD');
if (!$dsn || !$user || $password === false) {
    http_response_code(503);
    echo json_encode(['error' => 'service_unavailable']);
    exit;
}

try {
    $pdo = new PDO($dsn, $user, $password, [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_EMULATE_PREPARES => false,
    ]);
    $stmt = $pdo->prepare(
        'SELECT job_uuid, kind, status, requested_at, finished_at '
        . 'FROM ai_job WHERE tenant_id = :tenant_id AND job_uuid = :job_uuid LIMIT 1'
    );
    $stmt->execute(['tenant_id' => $tenantId, 'job_uuid' => $jobUuid]);
    $job = $stmt->fetch(PDO::FETCH_ASSOC);
    if ($job === false) {
        http_response_code(404);
        echo json_encode(['error' => 'not_found']);
        exit;
    }
    echo json_encode($job, JSON_UNESCAPED_SLASHES);
} catch (Throwable $e) {
    // Detailed errors belong in restricted service logs, never in public JSON.
    http_response_code(503);
    echo json_encode(['error' => 'service_unavailable']);
}
