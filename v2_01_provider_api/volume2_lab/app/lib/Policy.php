<?php
declare(strict_types=1);

final class Policy
{
    public static function tokenHash(string $token): string
    {
        return hash('sha256', $token);
    }

    public static function bearerToken(?string $header): string
    {
        if (!is_string($header) || !preg_match('/^Bearer ([A-Za-z0-9_-]{43,128})$/D', $header, $match)) {
            throw new InvalidArgumentException('Invalid bearer token');
        }
        return $match[1];
    }

    public static function idempotencyKey(?string $value): string
    {
        if (!is_string($value) || !preg_match('/^[A-Za-z0-9_-]{16,120}$/D', $value)) {
            throw new InvalidArgumentException('Invalid idempotency key');
        }
        return $value;
    }

    public static function parsePayload(string $raw, string $allowedModel): array
    {
        if (strlen($raw) === 0 || strlen($raw) > 16384) {
            throw new InvalidArgumentException('Request size out of bounds');
        }
        try {
            $value = json_decode($raw, true, 16, JSON_THROW_ON_ERROR);
        } catch (JsonException $e) {
            throw new InvalidArgumentException('Invalid JSON', 0, $e);
        }
        if (!is_array($value) || array_is_list($value)) {
            throw new InvalidArgumentException('JSON object required');
        }
        $fields = array_keys($value);
        foreach ($fields as $field) {
            if (!in_array($field, ['model', 'messages', 'stream', 'max_tokens'], true)) {
                throw new InvalidArgumentException('Unsupported field');
            }
        }
        if (($value['model'] ?? null) !== $allowedModel || ($value['stream'] ?? false) !== false) {
            throw new InvalidArgumentException('Unsupported model or streaming mode');
        }
        $messages = $value['messages'] ?? null;
        if (!is_array($messages) || count($messages) !== 1 || !is_array($messages[0])) {
            throw new InvalidArgumentException('Exactly one user message required');
        }
        $message = $messages[0];
        if (count($message) !== 2 || !array_key_exists('role', $message) || !array_key_exists('content', $message) || $message['role'] !== 'user' || !is_string($message['content'])) {
            throw new InvalidArgumentException('Invalid message');
        }
        $prompt = trim($message['content']);
        if ($prompt === '' || strlen($prompt) > 4000 || !preg_match('//u', $prompt)) {
            throw new InvalidArgumentException('Invalid prompt');
        }
        $maxTokens = $value['max_tokens'] ?? 256;
        if (!is_int($maxTokens) || $maxTokens < 1 || $maxTokens > 512) {
            throw new InvalidArgumentException('Invalid max_tokens');
        }
        return [
            'model' => $allowedModel,
            'messages' => [
                ['role' => 'system', 'content' => 'Answer concisely. Never claim to have executed tools.'],
                ['role' => 'user', 'content' => $prompt],
            ],
            'stream' => false,
            'max_tokens' => $maxTokens,
            'temperature' => 0.2,
        ];
    }

    public static function extractAnswer(string $raw): string
    {
        if (strlen($raw) > 131072) {
            throw new RuntimeException('Upstream response exceeds size limit');
        }
        try {
            $data = json_decode($raw, true, 32, JSON_THROW_ON_ERROR);
        } catch (JsonException $e) {
            throw new RuntimeException('Invalid upstream JSON', 0, $e);
        }
        $content = $data['choices'][0]['message']['content'] ?? null;
        if (!is_string($content) || $content === '' || strlen($content) > 32768 || !preg_match('//u', $content)) {
            throw new RuntimeException('Invalid upstream answer');
        }
        return $content;
    }

    public static function clientOutput(string $requestId, string $model, string $answer): array
    {
        return [
            'id' => $requestId,
            'object' => 'chat.completion',
            'model' => $model,
            'choices' => [[
                'index' => 0,
                'message' => ['role' => 'assistant', 'content' => $answer],
                'finish_reason' => 'stop',
            ]],
        ];
    }
}
