<?php
declare(strict_types=1);
require __DIR__.'/../app/core.php';
if (PHP_SAPI !== 'cli' || $argc !== 3) {
    fwrite(STDERR, "Usage: php create_user.php email role < /secure/stdin\n"); exit(2);
}
$email = $argv[1];
$role = $argv[2];
$password = trim((string)fgets(STDIN));
if (!filter_var($email, FILTER_VALIDATE_EMAIL) || !in_array($role, ['admin','reviewer','viewer'], true) || strlen($password) < 16) {
    fwrite(STDERR, "INVALID_INPUT\n"); exit(2);
}
$pdo = db(settings());
$stmt = $pdo->prepare('INSERT INTO users(email, pass_hash, role) VALUES (?, ?, ?)');
$stmt->execute([$email, password_hash($password, PASSWORD_DEFAULT), $role]);
echo "USER_CREATED\n";
