<?php
// Read-only CLI queue summary. Never expose this script as a public route.
declare(strict_types=1);
if (PHP_SAPI !== 'cli') {
    http_response_code(403);
    exit(1);
}
$path = getenv('LOCALAI_DB') ?: './state/workflow.sqlite3';
if (!is_file($path)) {
    fwrite(STDERR, "Database not found\n");
    exit(1);
}
$pdo = new PDO('sqlite:' . $path, null, null, [
    PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
    PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
]);
$pdo->exec('PRAGMA query_only=ON');
$stmt = $pdo->query('SELECT status, COUNT(*) AS total FROM jobs GROUP BY status ORDER BY status');
foreach ($stmt as $row) {
    printf("%-12s %d\n", $row['status'], (int)$row['total']);
}
