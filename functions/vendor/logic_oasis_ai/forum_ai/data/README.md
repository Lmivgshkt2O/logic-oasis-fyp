# Forum explanation-quality labels

This offline-only dataset must contain de-identified answer text and a reviewed
`label` using rubric version `forum-explanation-rubric-v1`:

- `sufficient_reasoning`: explains a method, relationship, or check; a final
  answer by itself is not enough.
- `needs_reasoning`: answer-only, copied prompt, or an assertion without a
  mathematical reason.

Keep provenance, consent/approval, author-grouped split where possible,
class balance, precision/recall/F1/confusion matrix, and calibration status in
the evaluation report. Seed/demo rows may test the pipeline but cannot support
supervisor-facing performance claims.

`emulator_reviewed_examples.jsonl` is a deliberately synthetic, developer
reviewed fixture. It exists only to verify the automatic emulator path. Replace
it only through an approved data release: retain an anonymous `authorGroup`, a
reviewer reference, provenance (`real` or `approved_external`), and never add
names, Firebase IDs, emails, or other identifiers.
