<?php
declare(strict_types=1);

final class Policy
{
    public static function tokenValid(string $authorization, string $storedHash): bool
    {
        if (!preg_match('/^Bearer ([A-Za-z0-9_-]{32,128})$/', $authorization, $match)) {
            return false;
        }
        return hash_equals($storedHash, hash('sha256', $match[1]));
    }

    public static function parsePrompt(string $body): ?string
    {
        if (strlen($body) > 8192) {
            return null;
        }
        try {
            $input = json_decode($body, true, 16, JSON_THROW_ON_ERROR);
        } catch (JsonException) {
            return null;
        }
        if (!is_array($input) || !isset($input['prompt']) || !is_string($input['prompt'])) {
            return null;
        }
        $prompt = trim($input['prompt']);
        if ($prompt === '' || strlen($prompt) > 4000 || !preg_match('//u', $prompt)) {
            return null;
        }
        return $prompt;
    }

    public static function upstreamPayload(string $prompt, string $model): array
    {
        return [
            'model' => $model,
            'stream' => false,
            'temperature' => 0.2,
            'max_tokens' => 256,
            'messages' => [
                ['role' => 'system', 'content' => 'Answer clearly. Never claim to have executed tools.'],
                ['role' => 'user', 'content' => $prompt],
            ],
        ];
    }
}
