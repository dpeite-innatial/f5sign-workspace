<?php
// Bench: the byte path of DocumentSigner for one signing act (custody read + digest check, inspect, apply,
// one seal into the drawn field, digest of the result), timed per phase, with PHP peak memory.
// S3 is simulated by the file read; the custody write is reduced to its digest.
// Written against the adapter's constructor as of 2026-10-27; adjust if TASK-074 changes it.
// usage: php pipeline.php file.pdf
declare(strict_types=1);

require '/var/www/html/vendor/autoload.php';

use F5Sign\Foundation\Time\SystemClock;
use F5Sign\SignatureExecution\Domain\Pdf\Request\FormRevision;
use F5Sign\SignatureExecution\Domain\Pdf\Request\SignatureFieldDefinition;
use F5Sign\SignatureExecution\Domain\Pdf\Request\SignRequest;
use F5Sign\SignatureExecution\Domain\Pdf\ValueObject\DigestAlgorithm;
use F5Sign\SignatureExecution\Domain\Pdf\ValueObject\SignatureLevel;
use F5Sign\SignatureExecution\Infrastructure\Pdf\DssHttpAdapter;
use F5Sign\SignatureExecution\Infrastructure\Pdf\DssPayloadMapper;
use F5Sign\SignatureExecution\Infrastructure\Pdf\MarkFont;
use F5Sign\SignatureExecution\Infrastructure\Pdf\MarkTextLayout;
use F5Sign\SignatureExecution\Infrastructure\Pdf\PyHankoFormEngine;
use Symfony\Component\HttpClient\HttpClient;

$file = $argv[1];
$ms = [];
$lap = static function (string $name, float &$t) use (&$ms): void {
    $now = hrtime(true);
    $ms[$name] = ($now - $t) / 1e6;
    $t = $now;
};

$dss = new DssHttpAdapter(
    HttpClient::createForBaseUri('http://eu-dss:8080', ['timeout' => 120.0, 'headers' => ['Accept' => 'application/json', 'Content-Type' => 'application/json']]),
    new DssPayloadMapper(new MarkTextLayout(MarkFont::fromFile('/var/www/html/assets/signature-execution/pt-serif-regular-advances.json'))),
    new SystemClock(),
    'certificate',
    timeoutSeconds: 120,
);
$forms = new PyHankoFormEngine('/opt/pyhanko/bin/python', '/var/www/html/assets/signature-execution/form_engine.py', '0.29.0', 60, 805306368);

$t = $t0 = hrtime(true);
$bytes = file_get_contents($file);
hash('sha256', $bytes);
$lap('read+digest', $t);

$forms->inspect($bytes);
$lap('inspect', $t);

$drawn = $forms->apply($bytes, new FormRevision([], [], [new SignatureFieldDefinition('sig1', 1, [100.0, 100.0, 300.0, 160.0], [])]));
$bytes = $drawn->pdf;
unset($drawn);
$lap('apply', $t);

$resp = $dss->seal(new SignRequest(base64_encode($bytes), basename($file), SignatureLevel::PADES_B_B, DigestAlgorithm::SHA256, null, 'sig1'));
$bytes = base64_decode($resp->signedPdfBase64, true);
unset($resp);
$lap('seal', $t);

hash('sha256', $bytes);
$lap('digest-out', $t);

printf("%s %.1fMB total=%.0fms php_peak=%.0fMB | %s\n", basename($file), filesize($file) / 1048576, (hrtime(true) - $t0) / 1e6,
    memory_get_peak_usage() / 1048576, implode(' ', array_map(static fn($k, $v) => sprintf('%s=%.0f', $k, $v), array_keys($ms), $ms)));
