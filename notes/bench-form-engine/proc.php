<?php
// Bench: the same form_engine `inspect` call fed three ways, to separate the engine's time from the pipe's.
// Speaks the pre-TASK-074 protocol (JSON + base64); it measures the "before".
// usage: php proc.php file.pdf
declare(strict_types=1);

require '/var/www/html/vendor/autoload.php';

use Symfony\Component\Process\Process;

$input = json_encode(['pdf' => base64_encode(file_get_contents($argv[1]))], JSON_THROW_ON_ERROR);
$cmd = ['/opt/pyhanko/bin/python', '-I', '/var/www/html/assets/signature-execution/form_engine.py', 'inspect', '--memory-limit-bytes', '805306368'];

$t = hrtime(true);
$p = new Process($cmd, null, [], $input, 300);
$p->run();
$a = (hrtime(true) - $t) / 1e6;

$t = hrtime(true);
$stream = fopen('php://temp', 'w+');
fwrite($stream, $input);
rewind($stream);
$p = new Process($cmd, null, [], $stream, 300);
$p->run();
$b = (hrtime(true) - $t) / 1e6;

$t = hrtime(true);
$tmp = tempnam(sys_get_temp_dir(), 'fe');
file_put_contents($tmp, $input);
$proc = proc_open($cmd, [0 => ['file', $tmp, 'r'], 1 => ['pipe', 'w'], 2 => ['pipe', 'w']], $pipes, null, []);
$out = stream_get_contents($pipes[1]);
stream_get_contents($pipes[2]);
$rc = proc_close($proc);
unlink($tmp);
$c = (hrtime(true) - $t) / 1e6;

printf("%s input=%.1fMB | Process(string)=%.0fms Process(stream)=%.0fms proc_open(file)=%.0fms rc=%d out=%d\n",
    basename($argv[1]), strlen($input) / 1048576, $a, $b, $c, $rc, strlen($out));
