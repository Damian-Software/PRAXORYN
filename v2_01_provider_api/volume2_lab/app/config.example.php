<?php
// Copy to /etc/local-ai/gateway.php with owner root and group www-data (0640).
// Never commit real credentials.
return [
    'dsn' => 'mysql:host=127.0.0.1;dbname=local_ai_gateway;charset=utf8mb4',
    'db_user' => 'gateway_runtime',
    'db_password' => 'REPLACE_WITH_DB_SECRET',
    'model' => 'REPLACE_WITH_MODEL_ID_FROM_GET_V1_MODELS',
    'upstream_url' => 'http://127.0.0.1:8080/v1/chat/completions',
    'upstream_token' => 'REPLACE_WITH_UPSTREAM_TOKEN',
];
