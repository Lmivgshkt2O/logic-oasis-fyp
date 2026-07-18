from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from build_function_bundle import build_bundle


class FunctionBundleParityTests(unittest.TestCase):
    def test_generated_manifest_matches_authoritative_sources(self) -> None:
        manifest = build_bundle()
        stored = json.loads((ROOT / "functions" / "vendor" / "bundle_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest, stored)
        self.assertEqual(manifest["bundleVersion"], "u8-ai-runtime-v1")
        self.assertTrue((ROOT / "functions" / "vendor" / "logic_oasis_ai" / "bkt.py").exists())


if __name__ == "__main__":
    unittest.main()
