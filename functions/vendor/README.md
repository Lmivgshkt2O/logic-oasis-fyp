# Generated U8 runtime bundle

`tools/build_function_bundle.py` copies the authoritative
`ai_pipeline/logic_oasis_ai` package and the three versioned configuration
files into this directory, then writes `bundle_manifest.json`.  Deploy from
the generated bundle only; do not hand-edit copied package files or substitute
the legacy `.pkl` model path.

The build command is deterministic and the parity test checks package and
policy hashes against the source tree before the Functions deploy step.
