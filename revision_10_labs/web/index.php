<?php
declare(strict_types=1);
// This example requires Nginx Basic auth on loopback and an authenticated REMOTE_USER.
// Never publish the PHP-FPM listener directly or trust REMOTE_USER from HTTP headers.
header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');
header('Referrer-Policy: no-referrer');
session_set_cookie_params(['httponly' => true, 'secure' => !empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off', 'samesite' => 'Strict']);
session_start();
if (empty($_SERVER['REMOTE_USER']) || !is_string($_SERVER['REMOTE_USER'])) {
    http_response_code(403);
    exit('Authenticated reverse proxy required.');
}
if (!isset($_SESSION['csrf'])) {
    $_SESSION['csrf'] = bin2hex(random_bytes(32));
}
$answer = '';
$error = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $provided = $_POST['csrf'] ?? '';
    if (!is_string($provided) || !hash_equals($_SESSION['csrf'], $provided)) {
        http_response_code(403);
        exit('Invalid CSRF token.');
    }
    $prompt = $_POST['prompt'] ?? '';
    if (!is_string($prompt) || trim($prompt) === '' || mb_strlen($prompt, 'UTF-8') > 4000) {
        $error = 'Prompt must contain 1 to 4000 characters.';
    } else {
        $keyPath = getenv('LOCALAI_API_TOKEN_FILE') ?: '/etc/localai-php/api_key.txt';
        $apiKey = is_readable($keyPath) ? trim((string)file_get_contents($keyPath)) : '';
        if ($apiKey === '') {
            $error = 'Server API credential unavailable.';
        } elseif (!function_exists('curl_init')) {
            $error = 'PHP cURL extension not installed.';
        } else {
            $payload = json_encode([
                'model' => 'local-chat',
                'messages' => [['role' => 'user', 'content' => $prompt]],
                'max_tokens' => 256,
                'temperature' => 0.2,
                'stream' => false
            ], JSON_THROW_ON_ERROR);
            $ch = curl_init('http://127.0.0.1:8081/v1/chat/completions');
            curl_setopt_array($ch, [
                CURLOPT_POST => true,
                CURLOPT_POSTFIELDS => $payload,
                CURLOPT_HTTPHEADER => ['Content-Type: application/json', 'Authorization: Bearer '.$apiKey],
                CURLOPT_RETURNTRANSFER => true,
                CURLOPT_TIMEOUT => 90,
                CURLOPT_CONNECTTIMEOUT => 3,
                CURLOPT_MAXREDIRS => 0,
                CURLOPT_FOLLOWLOCATION => false,
            ]);
            $raw = curl_exec($ch);
            $status = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
            curl_close($ch);
            if ($raw === false || $status !== 200 || strlen((string)$raw) > 1000000) {
                $error = 'Model service unavailable or returned an error.';
            } else {
                $decoded = json_decode((string)$raw, true);
                $content = $decoded['choices'][0]['message']['content'] ?? null;
                if (is_string($content)) $answer = $content;
                else $error = 'Unexpected model response.';
            }
        }
    }
}
function escapeHtml(string $value): string { return htmlspecialchars($value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8'); }
?>
<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Local AI / Pilot</title>
<style>body{max-width:54rem;margin:3rem auto;padding:0 1rem;font:1rem/1.6 system-ui,sans-serif}
textarea{box-sizing:border-box;width:100%;min-height:9rem;padding:.7rem}button{padding:.6rem 1.2rem}
pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f2f5f7;padding:1rem}</style>
</head><body><h1>Local AI / Pilot</h1>
<form action="/index.php" method="post"><input type="hidden" name="csrf" value="<?= escapeHtml($_SESSION['csrf']) ?>">
<label for="prompt">Prompt</label><textarea name="prompt" id="prompt" maxlength="4000" required></textarea>
<button type="submit">Send to local model</button></form>
<?php if ($error !== ''): ?><p role="alert"><?= escapeHtml($error) ?></p><?php endif; ?>
<?php if ($answer !== ''): ?><h2>Response</h2><pre><?= escapeHtml($answer) ?></pre><?php endif; ?>
</body></html>
