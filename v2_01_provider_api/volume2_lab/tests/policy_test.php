<?php
declare(strict_types=1);
require_once dirname(__DIR__) . '/app/lib/Policy.php';

$count = 0;
function ok(bool $condition, string $label): void {
    global $count;
    if (!$condition) throw new RuntimeException('FAIL: ' . $label);
    $count++;
}
function rejects(callable $fn, string $label): void {
    try { $fn(); } catch (InvalidArgumentException | RuntimeException $e) { ok(true, $label); return; }
    throw new RuntimeException('FAIL (accepted): ' . $label);
}
function payload(array $overrides = []): string {
    $base = ['model' => 'local-test', 'messages' => [['role'=>'user', 'content'=>'Hi']], 'stream'=>false, 'max_tokens'=>32];
    return json_encode(array_merge($base, $overrides), JSON_THROW_ON_ERROR | JSON_UNESCAPED_UNICODE);
}
$token = str_repeat('a', 43);
ok(Policy::bearerToken('Bearer ' . $token) === $token, 'bearer accepted');
rejects(fn() => Policy::bearerToken('Basic ' . $token), 'no Basic auth');
rejects(fn() => Policy::bearerToken('Bearer short'), 'token length');
rejects(fn() => Policy::bearerToken(null), 'missing auth');
rejects(fn() => Policy::bearerToken('Bearer ' . $token . ' '), 'whitespace');
ok(strlen(Policy::tokenHash($token)) === 64, 'token digest length');
ok(Policy::tokenHash('foo') !== Policy::tokenHash('bar'), 'token digest changes');
ok(Policy::idempotencyKey(str_repeat('b', 16)) === str_repeat('b', 16), 'idempotency accepted');
rejects(fn() => Policy::idempotencyKey('short'), 'short idempotency');
rejects(fn() => Policy::idempotencyKey('bad space key 1234'), 'idempotency spaces');
rejects(fn() => Policy::idempotencyKey(null), 'missing idem');
$valid = Policy::parsePayload(payload(), 'local-test');
ok($valid['model'] === 'local-test', 'model retained');
ok($valid['messages'][0]['role'] === 'system', 'system role pinned');
ok($valid['messages'][1]['content'] === 'Hi', 'user preserved');
ok($valid['max_tokens'] === 32, 'token cap accepted');
ok($valid['temperature'] === 0.2, 'temperature pinned');
rejects(fn() => Policy::parsePayload('', 'local-test'), 'empty payload');
rejects(fn() => Policy::parsePayload('{broken', 'local-test'), 'invalid json');
rejects(fn() => Policy::parsePayload('[]', 'local-test'), 'list rejected');
rejects(fn() => Policy::parsePayload('"plain"', 'local-test'), 'scalar rejected');
rejects(fn() => Policy::parsePayload(str_repeat('x', 16385), 'local-test'), 'body cap');
rejects(fn() => Policy::parsePayload(payload(['model'=>'other']), 'local-test'), 'model allowlist');
rejects(fn() => Policy::parsePayload(payload(['stream'=>true]), 'local-test'), 'no streaming');
rejects(fn() => Policy::parsePayload(payload(['tools'=>[]]), 'local-test'), 'no tools');
rejects(fn() => Policy::parsePayload(payload(['response_format'=>[]]), 'local-test'), 'no external schema');
rejects(fn() => Policy::parsePayload(payload(['messages'=>[]]), 'local-test'), 'no empty messages');
rejects(fn() => Policy::parsePayload(payload(['messages'=>[['role'=>'assistant','content'=>'x']]]), 'local-test'), 'no role spoof');
rejects(fn() => Policy::parsePayload(payload(['messages'=>[['role'=>'user','content'=>' ']]]), 'local-test'), 'no empty prompt');
rejects(fn() => Policy::parsePayload(payload(['messages'=>[['role'=>'user','content'=>str_repeat('x',4001)]]]), 'local-test'), 'prompt cap');
rejects(fn() => Policy::parsePayload(payload(['messages'=>[['role'=>'user','content'=>'Hi','metadata'=>['a'=>1]]]]), 'local-test'), 'no extra message props');
rejects(fn() => Policy::parsePayload("{\"model\":\"local-test\",\"messages\":[{\"role\":\"user\",\"content\":\"" . "\xFF" . "\"}]}", 'local-test'), 'invalid UTF-8');
rejects(fn() => Policy::parsePayload(payload(['max_tokens'=>0]), 'local-test'), 'lower max_tokens');
rejects(fn() => Policy::parsePayload(payload(['max_tokens'=>513]), 'local-test'), 'upper max_tokens');
rejects(fn() => Policy::parsePayload(payload(['max_tokens'=>'50']), 'local-test'), 'string max_tokens');
$swapped='{"model":"local-test","messages":[{"content":"Hello","role":"user"}],"stream":false}';
ok(Policy::parsePayload($swapped,'local-test')['messages'][1]['content']==='Hello', 'JSON order irrelevant');
$answer='{"choices":[{"message":{"content":"Hello."}}]}';
ok(Policy::extractAnswer($answer)==='Hello.', 'answer extracted');
rejects(fn()=>Policy::extractAnswer('{}'), 'missing answer');
rejects(fn()=>Policy::extractAnswer('{broken'), 'invalid upstream JSON');
rejects(fn()=>Policy::extractAnswer('{"choices":[{"message":{"content":[]}}]}'), 'array answer');
rejects(fn()=>Policy::extractAnswer('{"choices":[{"message":{"content":""}}]}'), 'empty answer');
rejects(fn()=>Policy::extractAnswer(str_repeat('x',131073)), 'upstream size cap');
$output=Policy::clientOutput('req_123','local-test','OK');
ok($output['choices'][0]['message']['content']==='OK', 'client response');
ok(!isset($output['usage']), 'no invented token usage');
echo "PASS {$count} PHP policy assertions\n";
