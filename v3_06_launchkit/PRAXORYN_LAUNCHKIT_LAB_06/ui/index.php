<?php
// Example read-only local page: do not publish without session authentication and CSRF protection.
declare(strict_types=1);
header('Content-Type: text/html; charset=utf-8');
header('Cache-Control: no-store');
function esc(string $value): string {
    return htmlspecialchars($value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}
$tokenPath = getenv('PXR_VIEW_TOKEN_FILE') ?: '';
if ($tokenPath === '' || !is_file($tokenPath)) {
    http_response_code(503);
    exit('Set PXR_VIEW_TOKEN_FILE to a protected read-scope token file.');
}
$token = trim((string) file_get_contents($tokenPath));
$ch = curl_init('http://127.0.0.1:8787/v1/jobs');
curl_setopt_array($ch, [
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_HTTPHEADER => ['Authorization: Bearer ' . $token, 'Accept: application/json'],
    CURLOPT_TIMEOUT => 8,
    CURLOPT_FOLLOWLOCATION => false,
]);
$body = curl_exec($ch);
$status = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);
if (!is_string($body) || $status !== 200) {
    http_response_code(502);
    exit('Local backend is unavailable or access was denied.');
}
$data = json_decode($body, true);
$jobs = is_array($data['jobs'] ?? null) ? $data['jobs'] : [];
?><!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Praxoryn LaunchKit - Read-only jobs</title>
<style>body{font:16px system-ui;margin:2rem auto;padding:0 1rem;max-width:60rem;color:#16303a}table{border-collapse:collapse;width:100%}th,td{padding:.6rem;border-bottom:1px solid #ccd6d9;text-align:left}th{background:#eff5f6}caption{text-align:left;margin-bottom:1rem}</style></head><body>
<h1>Local jobs</h1><p>Read-only teaching view. Draft results require manual approval.</p>
<table><caption>Latest jobs for the token's tenant</caption><thead><tr><th>ID</th><th>Kind</th><th>Status</th></tr></thead><tbody>
<?php foreach ($jobs as $job): ?>
<tr><td><?=esc((string)($job['id'] ?? ''))?></td><td><?=esc((string)($job['kind'] ?? ''))?></td><td><?=esc((string)($job['status'] ?? ''))?></td></tr>
<?php endforeach; ?>
</tbody></table></body></html>
