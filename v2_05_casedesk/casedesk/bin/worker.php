<?php
declare(strict_types=1);
require __DIR__.'/../app/core.php';
$settings=settings(); $pdo=db($settings);
$pdo->beginTransaction();
try {
    $r=$pdo->query("SELECT id,subject,body FROM cases WHERE status='queued' ORDER BY id LIMIT 1 FOR UPDATE SKIP LOCKED")->fetch();
    if (!$r) { $pdo->commit(); exit(0); }
    $s=$pdo->prepare("UPDATE cases SET status='processing',claimed_at=CURRENT_TIMESTAMP WHERE id=? AND status='queued'");
    $s->execute([$r['id']]); audit($pdo,(int)$r['id'],null,'case.processing');
    $pdo->commit();
} catch(Throwable $e) { if($pdo->inTransaction())$pdo->rollBack(); fwrite(STDERR,"CLAIM_FAILED\n");exit(1); }
try {
    $draft=modelReply((string)$settings['model']['endpoint'],(string)$settings['model']['id'],(string)$settings['model']['token'],(string)$r['subject'],(string)$r['body']);
    $pdo->beginTransaction();
    $s=$pdo->prepare('INSERT INTO drafts (case_id,content) VALUES (?,?)');$s->execute([$r['id'],$draft]);
    $s=$pdo->prepare("UPDATE cases SET status='pending_review', error_code=NULL WHERE id=? AND status='processing'");
    $s->execute([$r['id']]); audit($pdo,(int)$r['id'],null,'case.draft_ready');
    $pdo->commit();echo "DRAFT_READY\n";
} catch(Throwable $e) {
    if ($pdo->inTransaction()) $pdo->rollBack();
    $code=in_array($e->getMessage(),['ENDPOINT_NOT_LOCAL','ENDPOINT_PATH_INVALID','UPSTREAM_UNAVAILABLE','UPSTREAM_FORMAT'],true)?$e->getMessage():'WORKER_ERROR';
    $pdo->beginTransaction();
    $s=$pdo->prepare("UPDATE cases SET status='failed',error_code=? WHERE id=? AND status='processing'");
    $s->execute([$code,$r['id']]); audit($pdo,(int)$r['id'],null,'case.failed'); $pdo->commit();
    fwrite(STDERR,"JOB_FAILED: $code\n");exit(1);
}
