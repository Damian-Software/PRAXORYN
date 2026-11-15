<?php
declare(strict_types=1);

require_once dirname(__DIR__) . '/lib/Policy.php';
require_once dirname(__DIR__) . '/lib/Ledger.php';

function respond(int $status, array $body): never
{
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store');
    header('X-Content-Type-Options: nosniff');
    echo json_encode($body, JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR);
    exit;
}

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    header('Allow: POST');
    respond(405, ['error' => 'method_not_allowed']);
}

try {
    $config = require '/etc/local-ai/gateway.php';
    $token = Policy::bearerToken($_SERVER['HTTP_AUTHORIZATION'] ?? null);
    $idem = Policy::idempotencyKey($_SERVER['HTTP_IDEMPOTENCY_KEY'] ?? null);
    $raw = file_get_contents('php://input', false, null, 0, 16385);
    if ($raw === false) {
        throw new InvalidArgumentException('Cannot read input');
    }
    $payload = Policy::parsePayload($raw, $config['model']);
} catch (InvalidArgumentException $e) {
    respond(400, ['error' => 'invalid_request']);
} catch (Throwable $e) {
    respond(503, ['error' => 'configuration_unavailable']);
}

$requestId = 'req_' . bin2hex(random_bytes(16));
$started = hrtime(true);
try {
    $pdo = new PDO($config['dsn'], $config['db_user'], $config['db_password'], [
        PDO::ATTR_TIMEOUT => 3,
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_EMULATE_PREPARES => false,
    ]);
    $pdo->exec("SET time_zone = '+00:00'");
    $ledger = new Ledger($pdo);
    $ledger->reserve(Policy::tokenHash($token), $idem, $requestId);
} catch (DomainException $e) {
    $status = $e->getMessage() === 'quota_exceeded' ? 429 : 401;
    respond($status, ['error' => $status === 429 ? 'quota_exceeded' : 'unauthorized']);
} catch (PDOException $e) {
    if ($e->getCode() === '23000') {
        respond(409, ['error' => 'idempotency_conflict']);
    }
    respond(503, ['error' => 'ledger_unavailable']);
} catch (Throwable $e) {
    respond(503, ['error' => 'ledger_unavailable']);
}

$success = false;
$answer = null;
try {
    $handle = curl_init($config['upstream_url']);
    if ($handle === false) {
        throw new RuntimeException('Cannot initialize upstream client');
    }
    curl_setopt_array($handle, [
        CURLOPT_POST => true,
        CURLOPT_POSTFIELDS => json_encode($payload, JSON_THROW_ON_ERROR),
        CURLOPT_HTTPHEADER => [
            'Content-Type: application/json',
            'Authorization: Bearer ' . $config['upstream_token'],
        ],
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_CONNECTTIMEOUT => 3,
        CURLOPT_TIMEOUT => 60,
        CURLOPT_FOLLOWLOCATION => false,
        CURLOPT_PROTOCOLS => CURLPROTO_HTTP,
    ]);
    $body = curl_exec($handle);
    $httpStatus = curl_getinfo($handle, CURLINFO_RESPONSE_CODE);
    curl_close($handle);
    if (!is_string($body) || $httpStatus !== 200) {
        throw new RuntimeException('Upstream unavailable');
    }
    $answer = Policy::extractAnswer($body);
    $success = true;
} catch (Throwable $e) {
    $success = false;
}

$latencyMs = (int)floor((hrtime(true) - $started) / 1_000_000);
try {
    $ledger->settle($requestId, $success, $latencyMs);
} catch (Throwable $e) {
    respond(503, ['error' => 'settlement_unavailable', 'request_id' => $requestId]);
}
if (!$success) {
    respond(502, ['error' => 'upstream_failed', 'request_id' => $requestId]);
}
respond(200, Policy::clientOutput($requestId, $config['model'], $answer));
