<?php
// /var/www/localai/public/index.php
// Enforce HTTPS at the production reverse proxy.
$config = require dirname(__DIR__) . '/private.php';
$https = !empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off';
if (!$https) {
    http_response_code(403);
    exit('HTTPS required');
}
session_name('localai_session');
session_set_cookie_params([
    'lifetime' => 0, 'path' => '/', 'secure' => true,
    'httponly' => true, 'samesite' => 'Strict'
]);
session_start();
header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');
header('Referrer-Policy: no-referrer');
header('X-Frame-Options: DENY');
function esc(string $s): string {
    return htmlspecialchars($s, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}
function connection(array $cfg): PDO {
    return new PDO($cfg['dsn'], $cfg['db_user'], $cfg['db_password'], [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_EMULATE_PREPARES => false,
    ]);
}
if (!isset($_SESSION['csrf'])) {
    $_SESSION['csrf'] = bin2hex(random_bytes(32));
}
$error = '';
$answer = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $posted = (string)($_POST['csrf'] ?? '');
    if (!hash_equals($_SESSION['csrf'], $posted)) {
        http_response_code(403);
        exit('Invalid CSRF token');
    }
    if (isset($_POST['login'])) {
        $name = trim((string)($_POST['username'] ?? ''));
        $pass = (string)($_POST['password'] ?? '');
        if (strlen($name) > 120 || strlen($pass) > 4096) {
            $error = 'Invalid credentials.';
        } else {
            $stmt = connection($config)->prepare(
                'SELECT id,password_hash,active FROM users WHERE username=?'
            );
            $stmt->execute([$name]);
            $user = $stmt->fetch(PDO::FETCH_ASSOC);
            if ($user && $user['active'] &&
                password_verify($pass, $user['password_hash'])) {
                session_regenerate_id(true);
                $_SESSION['user_id'] = (int)$user['id'];
            } else {
                $error = 'Invalid credentials.';
            }
        }
    } elseif (isset($_POST['logout'])) {
        $_SESSION = [];
        session_destroy();
        header('Location: /');
        exit;
    } elseif (isset($_POST['ask']) && isset($_SESSION['user_id'])) {
        $prompt = trim((string)($_POST['prompt'] ?? ''));
        if ($prompt === '' || mb_strlen($prompt) > 4000) {
            $error = 'Prompt length must be between 1 and 4000 characters.';
        } else {
            $body = json_encode([
                'model' => $config['model'],
                'messages' => [['role'=>'user','content'=>$prompt]],
                'max_tokens' => 400, 'temperature' => 0.2,
            ], JSON_THROW_ON_ERROR);
            $curl = curl_init($config['gateway_url']);
            curl_setopt_array($curl, [
                CURLOPT_POST => true, CURLOPT_POSTFIELDS => $body,
                CURLOPT_RETURNTRANSFER => true,
                CURLOPT_CONNECTTIMEOUT => 5, CURLOPT_TIMEOUT => 120,
                CURLOPT_HTTPHEADER => [
                    'Content-Type: application/json',
                    'Authorization: Bearer ' . $config['gateway_key'],
                ],
            ]);
            $reply = curl_exec($curl);
            $status = curl_getinfo($curl, CURLINFO_HTTP_CODE);
            curl_close($curl);
            if ($reply === false || $status !== 200) {
                $error = 'The inference service is unavailable.';
            } else {
                $payload = json_decode($reply, true);
                $answer = (string)($payload['choices'][0]['message']['content'] ?? '');
            }
        }
    }
}
?>
<!doctype html><html lang="cs"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Local AI</title>
<style>
body{font:1rem/1.6 system-ui;background:#f4f6f8;color:#17222c;margin:0}
main{max-width:720px;margin:8vh auto;background:white;padding:2rem;border-radius:14px}
input,textarea,button{font:inherit;width:100%;box-sizing:border-box;padding:.7rem;margin:.4rem 0}
textarea{min-height:150px}button{background:#194a54;color:white;border:0;cursor:pointer}
pre{white-space:pre-wrap;overflow-wrap:anywhere}
</style></head><body><main><h1>Local AI</h1>
<?php if ($error !== ''): ?><p role="alert"><?=esc($error)?></p><?php endif; ?>
<?php if (!isset($_SESSION['user_id'])): ?>
<form method="post"><input type="hidden" name="csrf" value="<?=esc($_SESSION['csrf'])?>">
<label>Account <input name="username" required autocomplete="username"></label>
<label>Heslo <input name="password" type="password" required autocomplete="current-password"></label>
<button name="login" value="1">Sign in</button></form>
<?php else: ?>
<form method="post"><input type="hidden" name="csrf" value="<?=esc($_SESSION['csrf'])?>">
<label>Dotaz <textarea name="prompt" maxlength="4000" required></textarea></label>
<button name="ask" value="1">Odeslat</button></form>
<?php if ($answer !== ''): ?><h2>Response</h2><pre><?=esc($answer)?></pre><?php endif; ?>
<form method="post"><input type="hidden" name="csrf" value="<?=esc($_SESSION['csrf'])?>">
<button name="logout" value="1">Sign out</button></form>
<?php endif; ?></main></body></html>