<?php
declare(strict_types=1);
require __DIR__.'/../app/core.php';
$checks=[
    validCase('Request','Example body') === true,
    validCase('','Example body') === false,
    validCase('Request','') === false,
    validCase('Request',str_repeat('a',12001)) === false,
    isAllowed('admin','restricted') === true,
    isAllowed('reviewer','restricted') === false,
    isAllowed('reviewer','internal') === true,
    isAllowed('viewer','internal') === false,
    newCaseStatus('restricted') === 'manual_only',
    newCaseStatus('public') === 'queued',
    escape('<script>') === '&lt;script&gt;',
];
foreach($checks as $i=>$pass) {if (!$pass) {fwrite(STDERR,"FAIL case $i\n");exit(1);}}
echo 'PASS '.count($checks)." checks\n";
