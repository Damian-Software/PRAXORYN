<?php
declare(strict_types=1);
// Install outside the webroot as /etc/local-ai/portal.php with root:www-data, 0640.
return [
    'client_token_hash' => 'REPLACE_WITH_SHA256_OF_RANDOM_CLIENT_TOKEN',
    'model' => 'REPLACE_WITH_ID_FROM_V1_MODELS',
    'upstream_url' => 'http://127.0.0.1:8080/v1/chat/completions',
    'upstream_token' => 'REPLACE_WITH_SERVER_TOKEN',
    'db_dsn' => 'mysql:host=127.0.0.1;port=3306;dbname=local_ai;charset=utf8mb4',
    'db_user' => 'ai_audit',
    'db_password' => 'REPLACE_WITH_DATABASE_PASSWORD',
];
