# Annotation and redaction review

Use different fit rules for instructional highlights and privacy redactions. Never make a redaction
tighter merely to match a highlight aesthetically.

## Instructional highlights: target fit

Fit the outline to the logical target shown in the step:

- For a visible button, card, or tappable row, outline its full visible control boundary.
- For a state label or heading that is not a control, outline only the rendered label plus a small
  stroke-safe margin.
- For a grouped control such as a PIN keypad, include the complete visual group but exclude the
  surrounding panel, instructions, and unused whitespace.
- For an edge-aligned control, allow the outline to approach the image edge; do not add empty space
  merely to make the box symmetrical.

At full image resolution:

1. Place each side just outside the target so the stroke does not cover or clip it.
2. Exclude neighboring labels, controls, rows, and layout whitespace.
3. Confirm the number badge does not hide meaningful target text or an adjacent control.
4. Use an arrow only when a tight outline alone cannot make the target unambiguous.
5. Compare repeated controls across the guide and keep their visual margins consistent.

Reject a highlight when it describes a general area instead of clearly identifying the intended
target, or when any side could move inward without clipping the target or its stroke-safe margin.

## Privacy redactions: privacy fit

Cover every sensitive pixel with an intentional safety margin:

- Include antialiased glyph edges, ascenders, descenders, icons, avatars, and punctuation belonging
  to the sensitive value.
- Cover the entire row or content region when text wraps, record height varies, or nearby metadata
  could identify the subject.
- Check repeated copies in titles, breadcrumbs, notifications, status areas, lists, and dialogs.
- Prefer harmless over-coverage to a visually neat box that could reveal a character fragment.
- Keep the written reason specific enough for another reviewer to understand what was protected.

Never use blur, translucency, cropping, or an instructional highlight as a privacy control. The
pipeline's fixed opaque cover is the publishable redaction.

## Required review passes

Perform these passes independently on every image:

1. **Raw privacy inventory:** inspect the raw image at full resolution and enumerate every sensitive
   item before deciding that `redact: []` is safe.
2. **Reviewed privacy check:** inspect every edge of every opaque cover at full resolution and reject
   the image if any identifying fragment remains.
3. **Target-fit check:** ignore the redactions temporarily and verify that each highlight hugs the
   logical target without including unrelated space.
4. **Guide consistency check:** compare all reviewed images for consistent margin, numbering,
   legibility, and target semantics.

Archive a rejected reviewed-output directory beneath `private/runtime/`, adjust the specification,
rerun the exact retained run, and repeat all four passes. Approval applies only to the latest
regenerated set.
