<?php
// Laboratory-only read-only dashboard. Never publish without full authentication.
declare(strict_types=1);
header('Content-Security-Policy: default-src \'none\'; style-src \'self\'; form-action \'self\'');
header('X-Content-Type-Options: nosniff');
header('Referrer-Policy: no-referrer');
header('Cache-Control: no-store');
$tenant = $_GET['tenant'] ?? 'demo_school';
if (!is_string($tenant) || !preg_match('/^[a-z][a-z0-9_-]{2,39}$/D', $tenant)) {
    http_response_code(400);
    exit('Invalid tenant identifier');
}
$token = getenv('STUDIO_READ_TOKEN') ?: '';
if (strlen($token) < 24) {
    http_response_code(503);
    exit('Read token not configured');
}
$url = 'http://127.0.0.1:8769/jobs?tenant=' . rawurlencode($tenant);
$ctx = stream_context_create(['http' => [
    'method' => 'GET',
    'timeout' => 3,
    'ignore_errors' => true,
    'header' => "X-Read-Token: {$token}\r\nAccept: application/json\r\n"
]]);
$raw = @file_get_contents($url, false, $ctx);
$parsed = is_string($raw) ? json_decode($raw, true) : null;
$rows = is_array($parsed) && isset($parsed['jobs']) && is_array($parsed['jobs']) ? $parsed['jobs'] : [];
function e(string $text): string { return htmlspecialchars($text, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8'); }
?>
<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>PRAXORYN Studio — Local Jobs</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="/style.css"></head>
<body><main><h1>Local Jobs</h1>
<p>This dashboard is read-only and intended for loopback laboratory use.</p>
<form method="get"><label for="tenant">Tenant ID</label>
<input id="tenant" name="tenant" value="<?= e($tenant) ?>" maxlength="40" pattern="[a-z][a-z0-9_-]{2,39}" required>
<button type="submit">View</button></form>
<table><thead><tr><th>Job ID</th><th>Kind</th><th>Status</th><th>Attempts</th></tr></thead><tbody>
<?php foreach ($rows as $row): ?>
<tr><td><code><?= e((string)($row['id'] ?? '')) ?></code></td>
<td><?= e((string)($row['kind'] ?? '')) ?></td>
<td><?= e((string)($row['status'] ?? '')) ?></td>
<td><?= e((string)($row['attempts'] ?? '')) ?></td></tr>
<?php endforeach; ?>
</tbody></table></main></body></html>
