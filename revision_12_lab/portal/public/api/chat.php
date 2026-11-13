<?php
declare(strict_types=1);
require_once dirname(__DIR__, 2) . '/lib/Policy.php';

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');
$requestId = bin2hex(random_bytes(12));
$started = microtime(true);
$status = 503;

function respond(int $code, string $requestId, array $result): never
{
    http_response_code($code);
    echo json_encode(['request_id' => $requestId] + $result, JSON_THROW_ON_ERROR);
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    header('Allow: POST');
    respond(405, $requestId, ['error' => 'method_not_allowed']);
}
if (strlen((string) ($_SERVER['CONTENT_LENGTH'] ?? '0')) > 8192) {
    respond(413, $requestId, ['error' => 'payload_too_large']);
}
$config = require '/etc/local-ai/portal.php';
$authorization = (string) ($_SERVER['HTTP_AUTHORIZATION'] ?? '');
if (!Policy::tokenValid($authorization, $config['client_token_hash'])) {
    respond(401, $requestId, ['error' => 'unauthorized']);
}
$prompt = Policy::parsePrompt(file_get_contents('php://input', false, null, 0, 8193) ?: '');
if ($prompt === null) {
    respond(400, $requestId, ['error' => 'invalid_prompt']);
}

try {
    $db = new PDO($config['db_dsn'], $config['db_user'], $config['db_password'], [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_EMULATE_PREPARES => false,
        PDO::ATTR_TIMEOUT => 3,
    ]);
} catch (Throwable $error) {
    error_log("ai_gateway request_id=$requestId status=audit_unavailable");
    respond(503, $requestId, ['error' => 'service_unavailable']);
}

$payload = json_encode(Policy::upstreamPayload($prompt, $config['model']), JSON_THROW_ON_ERROR);
$curl = curl_init($config['upstream_url']);
curl_setopt_array($curl, [
    CURLOPT_POST => true,
    CURLOPT_POSTFIELDS => $payload,
    CURLOPT_HTTPHEADER => [
        'Content-Type: application/json',
        'Authorization: Bearer ' . $config['upstream_token'],
    ],
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_CONNECTTIMEOUT => 3,
    CURLOPT_TIMEOUT => 60,
    CURLOPT_FOLLOWLOCATION => false,
    CURLOPT_MAXREDIRS => 0,
]);
$responseBody = curl_exec($curl);
$upstreamStatus = (int) curl_getinfo($curl, CURLINFO_HTTP_CODE);
curl_close($curl);
$status = 502;
$answer = null;
if (is_string($responseBody) && strlen($responseBody) <= 1048576 && $upstreamStatus === 200) {
    try {
        $response = json_decode($responseBody, true, 32, JSON_THROW_ON_ERROR);
        $candidate = $response['choices'][0]['message']['content'] ?? null;
        if (is_string($candidate)) {
            $answer = $candidate;
            $status = 200;
        }
    } catch (JsonException) {
        // The upstream may return malformed JSON. No contents are logged.
    }
}
$durationMs = (int) round((microtime(true) - $started) * 1000);
try {
    $stmt = $db->prepare('INSERT INTO request_audit (request_id, status_code, duration_ms, upstream_status) VALUES (?, ?, ?, ?)');
    $stmt->execute([$requestId, $status, $durationMs, $upstreamStatus]);
} catch (Throwable $error) {
    error_log("ai_gateway request_id=$requestId status=audit_write_failed");
    respond(503, $requestId, ['error' => 'service_unavailable']);
}
if ($status !== 200) {
    respond(502, $requestId, ['error' => 'upstream_error']);
}
respond(200, $requestId, ['answer' => $answer]);
