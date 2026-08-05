# Phase 2 image pipeline

Status: Implemented
Date: 2026-08-05

## Contract

`guide-capture annotate <spec.json>` processes the PNG captures for the active Android run. The
specification must be a JSON file beneath `automation/specs/`. A step with ID `02` consumes
`runtime/raw-captures/<run-id>/02.png` and stages its result as
`reviewed-output/<slug>/02.android.png`.

The command does not publish files into the guides repository. Every result is marked as requiring
human review.

## Specification

```json
{
  "schema_version": 1,
  "slug": "hvordan-bruger-jeg-os2faktor",
  "start": {
    "type": "url",
    "value": "https://example.invalid/replace-with-approved-start-url"
  },
  "steps": [
    {
      "id": "02",
      "find": { "text": "Filer" },
      "expect_after": { "text": "Sikre filer" },
      "redact": [
        {
          "bounds": [40, 120, 420, 190],
          "reason": "account name"
        }
      ],
      "annotate": {
        "type": "highlight",
        "bounds": [40, 500, 1040, 650],
        "number": 2,
        "arrow_from": [900, 800]
      }
    }
  ]
}
```

Rules:

- `schema_version` is `1`.
- `slug` is a lowercase URL-safe slug.
- `start.type` is `url` or `package`; `start.value` is non-empty.
- `steps` is non-empty and every step ID is unique and filename-safe.
- Every step has a `redact` array, including `[]` when review finds nothing sensitive.
- Every redaction has `[left, top, right, bottom]` bounds and a written reason.
- `find` and `expect_after`, when present, use one exact semantic selector.
- `annotate` is optional. It draws one numbered highlight and may draw an arrow from
  `arrow_from` to the center of the highlighted region.
- Right and bottom bounds are exclusive. All coordinates must fit the source image.
- Unsupported or misspelled keys are errors.
- A system annotation font is verified by `doctor`.

## Processing order and safety

For every image, the helper validates the entire specification and every source-image dimension
before writing output. It then:

1. Draws fixed, opaque redaction covers.
2. Draws the optional arrow, highlight, and number badge.
3. Removes profiles, comments, EXIF, PNG date, and PNG time metadata.
4. Applies maximum PNG compression without changing image dimensions.
5. Writes the image and `annotation-report.json` with mode `600`.
6. Records the input/output paths, dimensions, SHA-256 hashes, redaction count, and review gate.

Existing reviewed images or reports are never overwritten. The operator must review or remove an
old staged result explicitly before processing a replacement. Symbolic links are rejected for the
reviewed-output root and per-guide output directory.

## Validation

- `python3 -m unittest discover -s tests -v`
- `shellcheck bin/guide-capture bin/check-sensitive-files`
- `/Users/dkp/.local/bin/prek run --all-files`
- `bin/guide-capture doctor`

Tests verify that missing redaction decisions and out-of-bounds coordinates fail before output,
redaction precedes annotation, metadata is stripped, hashes are recorded, permissions are private,
and existing reviewed output is not replaced.
