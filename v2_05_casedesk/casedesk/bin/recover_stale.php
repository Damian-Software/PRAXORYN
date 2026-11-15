<?php
declare(strict_types=1);
require __DIR__.'/../app/core.php';
if (PHP_SAPI!=='cli' || $argc!==2 || $argv[1]!=='--list-only') {fwrite(STDERR,"Usage: php recover_stale.php --list-only\n");exit(2);}
$pdo=db(settings());
$s=$pdo->query("SELECT id, claimed_at FROM cases WHERE status='processing' AND claimed_at < NOW() - INTERVAL 10 MINUTE ORDER BY claimed_at LIMIT 30");
foreach($s as $r) echo $r['id']."\t".$r['claimed_at']."\n";
// Intentionally no automatic reset: external side effects require human reconciliation.
