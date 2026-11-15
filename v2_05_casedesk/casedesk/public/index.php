<?php
declare(strict_types=1);
require __DIR__.'/../app/core.php';
try { $settings=settings(); } catch(Throwable $e) { http_response_code(503); exit('SERVICE_NOT_CONFIGURED'); }
ini_set('session.use_strict_mode', '1');
ini_set('session.use_only_cookies', '1');
session_name('CASE_DESK_SID');
session_set_cookie_params(['secure'=>(bool)$settings['app']['secure_cookie'],'httponly'=>true,'samesite'=>'Lax','path'=>'/']);
session_start();
header('X-Content-Type-Options: nosniff');
header('X-Frame-Options: DENY');
header("Content-Security-Policy: default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'");
header('Cache-Control: no-store');
if (($_SERVER['REQUEST_METHOD'] ?? '')==='GET' && ($_GET['action'] ?? '')==='health') { header('Content-Type: application/json'); exit('{"status":"ok"}'); }
try { $pdo=db($settings); } catch(Throwable $e) { http_response_code(503); exit('DB_UNAVAILABLE'); }
$method=$_SERVER['REQUEST_METHOD'] ?? 'GET';
$action=(string)($_GET['action'] ?? 'list');
$userId=(int)($_SESSION['user_id'] ?? 0);
$role=(string)($_SESSION['role'] ?? '');
function pageStart(string $title): void { echo '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>'.escape($title).'</title><style>body{font:16px system-ui;max-width:900px;margin:2rem auto;padding:0 1rem;line-height:1.5}input,textarea,select,button{font:inherit;padding:.5rem;margin:.3rem}textarea{width:100%}article{border:1px solid #aaa;padding:1rem;margin:.8rem 0}label{display:block}nav a{margin-right:1rem}</style>'; echo '<h1>'.escape($title).'</h1>'; }
function redirect(string $to='index.php'): never { header('Location: '.$to, true, 303); exit; }
if ($action==='login' && $method==='POST') {
    requireCsrf();
    $s=$pdo->prepare('SELECT id,pass_hash,role FROM users WHERE email=? AND active=1 LIMIT 1');
    $s->execute([substr((string)($_POST['email']??''),0,190)]); $u=$s->fetch();
    if (!$u || !password_verify((string)($_POST['password']??''),$u['pass_hash'])) { http_response_code(401); exit('LOGIN_FAILED'); }
    session_regenerate_id(true); $_SESSION['user_id']=(int)$u['id']; $_SESSION['role']=$u['role']; redirect();
}
if (!$userId) {
    pageStart('Sign in');
    echo '<form method="post" action="?action=login"><input type="hidden" name="csrf" value="'.escape(requestCsrf()).'"><label>Email<input name="email" type="email" autocomplete="username" required></label><label>Password<input type="password" name="password" autocomplete="current-password" required></label><button>Sign in</button></form></html>';
    exit;
}
if ($action==='logout' && $method==='POST') { requireCsrf(); $_SESSION=[]; session_destroy(); redirect(); }
if ($action==='create' && $method==='POST') {
    requireCsrf(); if (!in_array($role,['admin','reviewer'],true)) { http_response_code(403); exit('FORBIDDEN'); }
    $subject=trim((string)($_POST['subject']??'')); $body=trim((string)($_POST['body']??''));
    $classification=(string)($_POST['classification']??'');
    if (!in_array($classification,['public','internal','restricted'],true) || !validCase($subject,$body) || !isAllowed($role,$classification)) { http_response_code(422); exit('VALIDATION_FAILED'); }
    $pdo->beginTransaction();
    try {
        $s=$pdo->prepare('INSERT INTO cases (subject,body,classification,status,created_by) VALUES (?,?,?,?,?)');
        $s->execute([$subject,$body,$classification,newCaseStatus($classification),$userId]);
        audit($pdo,(int)$pdo->lastInsertId(),$userId,'case.created'); $pdo->commit();
    } catch(Throwable $e) { $pdo->rollBack(); throw $e; }
    redirect();
}
if ($action==='decision' && $method==='POST') {
    requireCsrf(); if (!in_array($role,['admin','reviewer'],true)) { http_response_code(403); exit('FORBIDDEN'); }
    $caseId=filter_var($_POST['id']??null,FILTER_VALIDATE_INT); $decision=(string)($_POST['decision']??'');
    if (!$caseId || !in_array($decision,['approved','rejected'],true)) { http_response_code(422); exit('INVALID_DECISION'); }
    $pdo->beginTransaction();
    try {
        $s=$pdo->prepare('SELECT classification,status FROM cases WHERE id=? FOR UPDATE'); $s->execute([$caseId]); $case=$s->fetch();
        if (!$case || $case['status']!=='pending_review' || !isAllowed($role,$case['classification'])) { $pdo->rollBack(); http_response_code(403); exit('NOT_REVIEWABLE'); }
        $s=$pdo->prepare('UPDATE cases SET status=? WHERE id=?');$s->execute([$decision,$caseId]);
        $s=$pdo->prepare('UPDATE drafts SET reviewed_by=?,reviewed_at=CURRENT_TIMESTAMP WHERE case_id=?');$s->execute([$userId,$caseId]);
        audit($pdo,$caseId,$userId,'case.'.$decision); $pdo->commit();
    } catch(Throwable $e) { if($pdo->inTransaction())$pdo->rollBack(); throw $e; }
    redirect();
}
pageStart('CaseDesk');
echo '<nav>Review AI-assisted drafts manually. <form method="post" action="?action=logout" style="display:inline"><input type="hidden" name="csrf" value="'.escape(requestCsrf()).'"><button>Sign out</button></form></nav>';
if (in_array($role,['admin','reviewer'],true)) {
    echo '<h2>New case</h2><form method="post" action="?action=create"><input type="hidden" name="csrf" value="'.escape(requestCsrf()).'"><label>Subject<input name="subject" maxlength="180" required></label><label>Message<textarea name="body" maxlength="4000" rows="5" required></textarea></label><label>Classification<select name="classification"><option value="public">public</option><option value="internal">internal</option>';
    if ($role==='admin') echo '<option value="restricted">restricted (manual only)</option>';
    echo '</select></label><button>Create case</button></form>';
}
$stmt=$pdo->query('SELECT c.id,c.subject,c.body,c.classification,c.status,d.content FROM cases c LEFT JOIN drafts d ON d.case_id=c.id ORDER BY c.id DESC LIMIT 50');
foreach ($stmt as $r) {
    if (!isAllowed($role,$r['classification'])) continue;
    echo '<article><h2>#'.(int)$r['id'].' '.escape($r['subject']).'</h2><p>Class: '.escape($r['classification']).' | Status: '.escape($r['status']).'</p><p>'.nl2br(escape($r['body'])).'</p>';
    if ($r['content']!==null) echo '<h3>Draft</h3><pre style="white-space:pre-wrap">'.escape($r['content']).'</pre>';
    if ($r['status']==='pending_review' && in_array($role,['admin','reviewer'],true)) {
        foreach(['approved','rejected'] as $dec) echo '<form method="post" action="?action=decision" style="display:inline"><input type="hidden" name="csrf" value="'.escape(requestCsrf()).'"><input type="hidden" name="id" value="'.(int)$r['id'].'"><input type="hidden" name="decision" value="'.$dec.'"><button>'.escape(ucfirst($dec)).'</button></form>';
    }
    echo '</article>';
}
echo '</html>';
