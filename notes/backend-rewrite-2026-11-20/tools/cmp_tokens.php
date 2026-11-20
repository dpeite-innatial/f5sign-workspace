<?php
// For each changed PHP file: compare token streams with comments and whitespace dropped.
// Prints a line per file whose non-comment tokens differ, with the first differing token pair.
$skip = [T_COMMENT, T_DOC_COMMENT, T_WHITESPACE];
$same = 0; $diff = 0; $strOnly = 0;
foreach (file('/w/cmp/changed.txt', FILE_IGNORE_NEW_LINES) as $f) {
    $a = @file_get_contents("/w/cmp/a/$f"); $b = @file_get_contents("/w/cmp/b/$f");
    if ($a === false || $b === false) { echo "MISSING $f\n"; continue; }
    $ta = array_values(array_filter(token_get_all($a), fn($t) => !is_array($t) || !in_array($t[0], $skip, true)));
    $tb = array_values(array_filter(token_get_all($b), fn($t) => !is_array($t) || !in_array($t[0], $skip, true)));
    $norm = fn($t) => is_array($t) ? [$t[0], $t[1]] : [0, $t];
    $na = array_map($norm, $ta); $nb = array_map($norm, $tb);
    if ($na === $nb) { $same++; continue; }
    $onlyStrings = count($na) === count($nb);
    $first = null;
    for ($i = 0; $i < min(count($na), count($nb)); $i++) {
        if ($na[$i] !== $nb[$i]) {
            $first ??= $i;
            if (!in_array($na[$i][0], [T_CONSTANT_ENCAPSED_STRING, T_ENCAPSED_AND_WHITESPACE], true)) { $onlyStrings = false; }
        }
    }
    if ($onlyStrings) { $strOnly++; echo "STRING $f :: " . substr($na[$first][1], 0, 90) . " => " . substr($nb[$first][1], 0, 90) . "\n"; continue; }
    $diff++;
    $i = $first ?? min(count($na), count($nb));
    echo "CODE $f :: " . token_name($na[$i][0] ?: 0) . ' ' . substr($na[$i][1] ?? '', 0, 80) . ' => ' . substr($nb[$i][1] ?? '', 0, 80) . "\n";
}
fwrite(STDERR, "same=$same stringsOnly=$strOnly code=$diff\n");
