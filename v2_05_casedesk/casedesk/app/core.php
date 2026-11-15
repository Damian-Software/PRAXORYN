<?php
declare(strict_types=1);
function settings(): array {
    $path = getenv('CASE_DESK_CONFIG') ?: '/etc/casedesk.ini';
    $data = parse_ini_file($path, true, INI_SCANNER_TYPED);
    if (!is_array($data) || !isset($data['db'], $data['model'], $data['app'])) {
        throw new RuntimeException('CONFIG_INVALID');
    }
    return $data;
}
function db(array $settings): PDO {
    $d = $settings['db'];
    return new PDO('mysql:host='.$d['host'].';dbname='.$d['name'].';charset=utf8mb4',
        (string)$d['user'], (string)$d['password'], [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            PDO::ATTR_EMULATE_PREPARES => false,
        ]);
}
function escape(string $value): string {
    return htmlspecialchars($value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}
function isAllowed(string $role, string $classification): bool {
    $levels = ['viewer'=>0,'reviewer'=>1,'admin'=>2];
    $required = ['public'=>0,'internal'=>1,'restricted'=>2];
    return isset($levels[$role], $required[$classification]) && $levels[$role] >= $required[$classification];
}
function newCaseStatus(string $classification): string {
    return $classification === 'restricted' ? 'manual_only' : 'queued';
}
function validCase(string $subject, string $body): bool {
    return $subject !== '' && strlen($subject) <= 540 && $body !== '' && strlen($body) <= 12000;
}
function audit(PDO $pdo, ?int $caseId, ?int $actorId, string $action): void {
    $stmt = $pdo->prepare('INSERT INTO audit_events (case_id, actor_id, action) VALUES (?, ?, ?)');
    $stmt->execute([$caseId, $actorId, $action]);
}
function requestCsrf(): string {
    if (!isset($_SESSION['csrf'])) { $_SESSION['csrf'] = bin2hex(random_bytes(32)); }
    return (string)$_SESSION['csrf'];
}
function requireCsrf(): void {
    if (!hash_equals(requestCsrf(), (string)($_POST['csrf'] ?? ''))) {
        http_response_code(403); exit('CSRF_REJECTED');
    }
}
function modelReply(string $endpoint, string $model, string $token, string $subject, string $body): string {
    $parts = parse_url($endpoint);
    if (!is_array($parts) || ($parts['scheme'] ?? '') !== 'http' || !in_array($parts['host'] ?? '', ['127.0.0.1','localhost'], true)) {
        throw new RuntimeException('ENDPOINT_NOT_LOCAL');
    }
    if (!str_ends_with((string)($parts['path'] ?? ''), '/v1/chat/completions')) {
        throw new RuntimeException('ENDPOINT_PATH_INVALID');
    }
    $payload = json_encode([
        'model'=>$model, 'stream'=>false, 'max_tokens'=>300,
        'messages'=>[
            ['role'=>'system','content'=>'Draft a neutral support reply. Do not invent facts, approvals, payments or promises. Output only a draft for human review.'],
            ['role'=>'user','content'=>"Subject: $subject\nMessage: $body"],
        ],
    ], JSON_THROW_ON_ERROR);
    $ch = curl_init($endpoint);
    if ($ch === false) { throw new RuntimeException('CURL_INIT'); }
    curl_setopt_array($ch, [
        CURLOPT_POST=>true, CURLOPT_POSTFIELDS=>$payload, CURLOPT_RETURNTRANSFER=>true,
        CURLOPT_TIMEOUT=>90, CURLOPT_CONNECTTIMEOUT=>4,
        CURLOPT_HTTPHEADER=>['Content-Type: application/json','Authorization: Bearer '.$token],
        CURLOPT_FOLLOWLOCATION=>false, CURLOPT_PROTOCOLS=>CURLPROTO_HTTP,
    ]);
    $bodyJson = curl_exec($ch);
    $status = curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
    $err = curl_errno($ch);
    curl_close($ch);
    if ($bodyJson === false || $err !== 0 || $status !== 200 || strlen((string)$bodyJson)>300000) {
        throw new RuntimeException('UPSTREAM_UNAVAILABLE');
    }
    $result = json_decode((string)$bodyJson, true, 32, JSON_THROW_ON_ERROR);
    $content = $result['choices'][0]['message']['content'] ?? null;
    if (!is_string($content) || trim($content)==='' || strlen($content)>36000) {
        throw new RuntimeException('UPSTREAM_FORMAT');
    }
    return trim($content);
}
