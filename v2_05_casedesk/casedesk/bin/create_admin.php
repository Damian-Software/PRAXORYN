<?php
declare(strict_types=1);
require __DIR__.'/../app/core.php';
if (PHP_SAPI!=='cli' || $argc!==2) { fwrite(STDERR,"Usage: php create_admin.php email < /secure/path/admin-password.txt\n");exit(2); }
$email=$argv[1]; $password=trim((string)fgets(STDIN));
if (!filter_var($email,FILTER_VALIDATE_EMAIL) || strlen($password)<16) {fwrite(STDERR,"INVALID_INPUT\n");exit(2);}
$pdo=db(settings());
$s=$pdo->prepare("INSERT INTO users(email,pass_hash,role) VALUES (?,?,'admin')");
$s->execute([$email,password_hash($password,PASSWORD_DEFAULT)]);
echo "ADMIN_CREATED\n";
