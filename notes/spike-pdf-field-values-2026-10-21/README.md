# Spike: valores de campo en el PDF sin romper firmas (2026-10-21)

Contexto: BL-269 (los valores registrados no llegan a ningún documento), BL-42 (FieldMDP), BL-366 (geometría).
Medido contra el `eu-dss` 6.4 del stack local y pyHanko 0.29.0 en un contenedor desechable
(`Dockerfile` de esta carpeta, red `f5sign-net`). Nada se ejecutó en el host.

## Cómo reproducir

```sh
docker build -t f5spike-pyhanko:1 .
docker run --rm --user $(id -u):$(id -g) -e HOME=/tmp --network f5sign-net -v $PWD:/w f5spike-pyhanko:1 \
  sh -c 'python spike.py B directn && python analyze.py out/B-directn/5-tampered.report.json'
```

`spike.py <cadena> [flags]`:
- `A`: DSS crea sus campos de firma.
- `B`: precreamos los campos de firma con `/Lock` y DSS firma dentro (`fieldParameters.fieldId`).
- `C`: igual que B, pero firma pyHanko.
- Flags: `directn` (forma final), `merge`, `newap`, `prefill` y `nofill2` (variantes de diagnóstico).

Secuencia de cada cadena:
1. Preparar los campos (solo lectura, prefijo `f5s_`, un widget por ocurrencia).
2. Rellenar los valores del firmante 1.
3. Firma 1.
4. Rellenar los valores del firmante 2.
5. Firma 2.
6. Manipular: cambiar en una revisión posterior un valor del firmante 1.

## Resultados

| # | Pregunta | Resultado medido |
|---|---|---|
| 1 | ¿Rellenar campos creados antes de la firma 1, en revisiones posteriores, invalida firmas en DSS? | **No.** Todas las modificaciones salen como `SignatureOrFormFill`, con `Undefined: 0`. La integridad criptográfica es OK. La indicación es `INDETERMINATE/NO_CERTIFICATE_CHAIN_FOUND`, igual que la cadena de control: es el sello de desarrollo, que no es de confianza. |
| 2 | ¿Aparece algún aviso nuevo? | **Sí, un WARNING:** *"Visual difference is detected on page(s) [1]"* en la firma 1. La cadena de control (dos firmas DSS sin campos) **no** lo da: es nuevo y lo produce el relleno. No cambia la indicación. |
| 3 | ¿DSS escribe FieldMDP si firma dentro de un campo con `/Lock`? | **Sí.** El diccionario de firma lleva `FieldMDP` (`INCLUDE`, los campos del firmante) y DSS informa `SigFieldLock`. |
| 4 | ¿DSS **detecta** que se cambie un campo bloqueado después de la firma? | **No.** En `5-tampered`, *"Is signature valid against /FieldMDP dictionary?"* da OK. La manipulación se clasifica como relleno legítimo y solo deja el mismo WARNING de diferencia visual. Probado con y sin `/Kids`, y con nombres con y sin punto. |
| 4b | ¿Por qué no lo detecta DSS? | Lo descompilé de `dss-pades-6.4.jar`/`dss-validation-6.4.jar` del contenedor. El control (`AbstractPdfLockDictionaryCheck`) compara los campos bloqueados con `pdfRevision.getModifiedFieldNames()`. Esa lista sale de `ObjectModification.getFieldName()`, que solo devuelve un nombre si **el objeto modificado es un diccionario con `/T`**. Pero el comparador (`DefaultPdfObjectModificationsFinder.compareSimpleObjects`) baja hasta la hoja y registra el cambio sobre el **valor simple** (el string de `/V`), no sobre el diccionario del campo. Resultado: `fieldName = null`, la lista de campos modificados llega vacía y el control pasa sin comparar nada. **Limitación del código de DSS 6.4, no de configuración ni de cómo construimos el PDF**: solo vería un campo bloqueado si se creara o borrara entero. **6.5.1 (la última, 2026-10) tampoco lo corrige**: descompilada, `ObjectModification.getFieldName()` y `AbstractPdfLockDictionaryCheck` son idénticos. Lo único que cambia en ese código es `checkSigFieldsConsistency` (DSS-3946), que vigila la apariencia de los campos de **firma**, no los de datos. |
| 5 | ¿DSS toca campos ajenos al firmar? | En la cadena **A** (DSS crea el campo de firma), su revisión **vuelve a escribir los widgets de la página con el mismo contenido** (comparado clave a clave: ningún cambio), porque añade su campo a `/Annots` y guarda en modo incremental. Ni DSS (`Undefined: 0`) ni Adobe (PDFs 1 y 4) lo marcan. En la cadena **B** (firma dentro de un campo nuestro) solo toca el Catalog, el AcroForm y su propio campo. **No es motivo para crear los campos de firma nosotros; el único motivo es el `/Lock`.** No medido: una firma anterior con bloqueo seguida de una firma en la que DSS crea su propio campo. |
| 6 | ¿Sirve pyHanko como validador? | **No tal como está.** Detecta la manipulación (*"form field f5s_name is locked"*), pero también da por manipulado el caso legítimo: marca la firma 1 por un objeto que se crea en la revisión 1 y no se toca nunca más (comprobado con `get_last_change`). Es un falso positivo con nuestra estructura, y además falla con `/Kids` (*"unexplained xrefs"*) y con un `/AP /N` directo en un campo fusionado (excepción). |
| 7 | ¿Firma pyHanko dentro de los campos bloqueados? | Sí (cadena C). DSS valida esas firmas igual que las suyas: el mismo FieldMDP y los mismos resultados. |
| 8 | Visual | El texto (Helvetica, WinAnsi, con acentos), el desplegable y el checkbox (ZapfDingbats ✔) se pintan bien. En la página `/Rotate 90` con el CropBox desplazado, el valor se lee derecho en pantalla con `/MK /R 90` y `/Matrix [0 1 -1 0 0 0]`. |

## Reglas de construcción que salieron de la prueba

- **Los nombres parciales de campo no llevan punto.** `f5s.name` es un nombre jerárquico; pyHanko lo rechaza. Se usa `f5s_<id>`.
- **El diccionario de estados `/AP /N` de un checkbox va directo, no indirecto.** Si es indirecto, poppler no lo pinta.
- **Los campos de firma se precrean** (con `/Lock`), y DSS firma dentro con `fieldId`. Si DSS crea el campo, reescribe widgets ajenos.
- Los campos se crean **solo lectura** desde el principio; el valor lo ponemos nosotros, sin `NeedAppearances`.
- Un campo con N ocurrencias es un campo con N `/Kids`, y todos los widgets comparten `/V` (ADR-0041).
- El relleno actualiza `/V` y la apariencia. Para DSS dan igual las dos formas (sustituir el stream en el sitio o crear uno nuevo y apuntar el widget a él).

## Conclusión

- **El mecanismo funciona con DSS como firmante**, en los dos modos. No hace falta cambiar de firmante para pintar valores.
- **FieldMDP se escribe, pero ninguno de los dos validadores automáticos probados lo hace cumplir bien**: DSS no detecta la manipulación, y pyHanko también marca lo legítimo. Adobe sí (ver abajo).
- **Adobe Reader sí aplica FieldMDP** (resultado abajo). El bloqueo merece la pena: el validador que abre el
  destinatario invalida la firma de quien rellenó si un valor suyo cambia después. DSS y pyHanko no son la vara de
  medir para esta propiedad, y un test automático de ella necesita otro validador o una comprobación nuestra.

## Prueba en Adobe Reader (hecha por el owner, 2026-10-21)

Resultado observado (el certificado sale con identidad desconocida en todos, porque es el sello de desarrollo):
- `2-bloqueado-legitimo.pdf`: sin firma inválida. Bajo la firma 1 aparece "Form Fields Filled In: f5s_country" como
  cambio posterior; la firma 2 dice "Document has not been modified since this signature was applied".
- `3-bloqueado-manipulado.pdf`: **la firma 1 sale inválida**, con "There have been changes made to this document that
  invalidate…" ("At least one signature is invalid"). El relleno de `f5s_name` aparece con un aviso.
- `4-sin-bloqueo-manipulado.pdf`: **ninguna firma inválida**. Solo "There have been subsequent changes" y el relleno
  de `f5s_name`, con un aviso amarillo. Sin bloqueo, la manipulación pasa.

Lo que se esperaba antes de abrirlos:

Los PDFs están en `adobe/`. En todos, el certificado sale como desconocido o no de confianza (es el sello de desarrollo); eso hay que ignorarlo. Lo que se mira es el **panel de firmas**: el estado de integridad de cada firma y la lista de cambios.

| Fichero | Firmas | Qué se espera |
|---|---|---|
| `1-control-sin-campos.pdf` | 2 | Ninguna con cruz roja de "documento alterado". |
| `2-bloqueado-legitimo.pdf` | 2 | Ninguna con cruz roja. La firma 1 lista cambios posteriores permitidos (relleno de formulario y firma). |
| `3-bloqueado-manipulado.pdf` | 2 | **La firma 1 inválida o con cambios no permitidos** (se cambió `f5s_name`, que estaba bloqueado). Si sale válida, FieldMDP no lo hace cumplir ningún validador de los probados. |
| `4-sin-bloqueo-manipulado.pdf` | 2 | Sin cruz roja: sin bloqueo, la manipulación pasa por relleno legítimo. |
