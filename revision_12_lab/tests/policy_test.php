<?php
declare(strict_types=1);
require dirname(__DIR__) . '/portal/lib/Policy.php';
function check(bool $condition, string $label): void {
    if (!$condition) { throw new RuntimeException("FAIL: $label"); }
    echo "PASS: $label\n";
}
$token = str_repeat('A', 32);
$hash = hash('sha256', $token);
check(Policy::tokenValid('Bearer ' . $token, $hash), 'valid token');
check(!Policy::tokenValid('Bearer ' . str_repeat('B', 32), $hash), 'wrong token');
check(!Policy::tokenValid('Basic ' . $token, $hash), 'reject basic auth');
check(!Policy::tokenValid('Bearer abc', $hash), 'reject short token');
check(Policy::parsePrompt('{"prompt":"Hello"}') === 'Hello', 'valid prompt');
check(Policy::parsePrompt('{"prompt":"   "}') === null, 'blank prompt');
check(Policy::parsePrompt('{"prompt":4}') === null, 'nonstring prompt');
check(Policy::parsePrompt('{broken json') === null, 'invalid JSON');
check(Policy::parsePrompt('{"prompt":"' . str_repeat('x', 4001) . '"}') === null, 'prompt over limit');
check(Policy::parsePrompt('{"prompt":"Hi"}') !== null, 'short prompt');
$payload = Policy::upstreamPayload('Verify', 'local-model');
check($payload['messages'][1]['role'] === 'user', 'fixed role');
check($payload['stream'] === false, 'streaming off');
echo "12 tests passed\n";
