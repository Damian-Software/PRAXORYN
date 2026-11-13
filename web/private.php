<?php
// /var/www/localai/private.php – outside the public web root.
return [
  'dsn' => 'mysql:host=localhost;dbname=localai_web;charset=utf8mb4',
  'db_user' => 'localai_web',
  'db_password' => getenv('LOCALAI_DB_PASSWORD'),
  'gateway_url' => 'http://127.0.0.1:8000/v1/chat/completions',
  'gateway_key' => getenv('LOCALAI_GATEWAY_KEY'),
  'model' => 'local-qwen3-4b',
];