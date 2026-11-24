<?php
// Bench: form_engine `apply` with the input as a string vs as a stream; then the real adapter with the configured 20 s timeout.
// The first two runs speak the pre-TASK-074 protocol (JSON + base64); the third goes through the adapter as it is.
declare(strict_types=1);
require '/var/www/html/vendor/autoload.php';
use F5Sign\SignatureExecution\Infrastructure\Pdf\PyHankoFormEngine;
use Symfony\Component\Process\Process;
$pdf = file_get_contents($argv[1]);
$input = json_encode(['pdf' => base64_encode($pdf), 'create' => [], 'fill' => [], 'signatureFields' => [['name' => 'sig1', 'page' => 1, 'rect' => [100, 100, 300, 160], 'lock' => []]]], JSON_THROW_ON_ERROR);
$cmd = ['/opt/pyhanko/bin/python', '-I', '/var/www/html/assets/signature-execution/form_engine.py', 'apply', '--memory-limit-bytes', '805306368'];
$t = hrtime(true); $s = fopen('php://temp', 'w+'); fwrite($s, $input); rewind($s);
$p = new Process($cmd, null, [], $s, 300); $p->run(); $b = (hrtime(true) - $t) / 1e6; $outLen = strlen($p->getOutput());
$t = hrtime(true); $p = new Process($cmd, null, [], $input, 300); $p->run(); $a = (hrtime(true) - $t) / 1e6;
$t = hrtime(true);
try { (new PyHankoFormEngine('/opt/pyhanko/bin/python', '/var/www/html/assets/signature-execution/form_engine.py', '0.29.0', 20, 805306368))->inspect($pdf); $r = 'ok'; }
catch (Throwable $e) { $r = get_class($e) . ':' . ($e->kind->name ?? $e->getMessage()); }
$c = (hrtime(true) - $t) / 1e6;
printf("%s apply: string=%.0fms stream=%.0fms out=%.1fMB | real inspect @20s timeout: %s in %.0fms\n", basename($argv[1]), $a, $b, $outLen / 1048576, $r, $c);
