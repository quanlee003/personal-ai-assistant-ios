"""Package the pinned official WDA archive locally; never sign or install it."""
import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import zipfile

ROOT = Path(__file__).resolve().parents[1] / "artifacts" / "direct-setup"
SHA256 = "4209939f45d66b1fbd8e036effcc13637cddceaa12e3db8636c47ca645e2ebc5"
APP = "WebDriverAgentRunner-Runner.app/"


def prepare(source: Path, output: Path, *, omit_debug_symbols: bool = False):
    if hashlib.sha256(source.read_bytes()).hexdigest() != SHA256:
        raise ValueError("Archive does not match official WDA 17.0.2 SHA256")
    with zipfile.ZipFile(source) as archive:
        names = archive.namelist()
        if any(not n.startswith(APP) or ".." in n.split("/") for n in names):
            raise ValueError("Unexpected archive layout")
        info = plistlib.loads(archive.read(APP + "Info.plist"))
        if info.get("CFBundleSupportedPlatforms") != ["iPhoneOS"]:
            raise ValueError("Not a real iPhone build")
        runner = APP + "PlugIns/WebDriverAgentRunner.xctest/"
        archive.getinfo(runner + "WebDriverAgentRunner")
        archive.getinfo(APP + info["CFBundleExecutable"])
        debug_prefix = APP + "PlugIns/WebDriverAgentRunner.xctest.dSYM/"
        removed = []
        with zipfile.ZipFile(output, "x", zipfile.ZIP_DEFLATED) as ipa:
            for entry in archive.infolist():
                if omit_debug_symbols and entry.filename.startswith(debug_prefix):
                    removed.append(entry.filename)
                    continue
                new_entry = zipfile.ZipInfo("Payload/" + entry.filename, entry.date_time)
                new_entry.external_attr = entry.external_attr
                new_entry.compress_type = zipfile.ZIP_DEFLATED
                ipa.writestr(new_entry, archive.read(entry))
    with zipfile.ZipFile(output) as ipa:
        if ipa.testzip() is not None:
            raise ValueError("IPA integrity check failed")
        assert "Payload/" + runner + "WebDriverAgentRunner" in ipa.namelist()
    return {"wda_version": "17.0.2", "source_sha256": SHA256,
            "ipa_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            "bundle_id": info["CFBundleIdentifier"], "entries": len(names) - len(removed),
            "omitted_debug_entries": removed,
            "signed_for_device": False, "installed": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--omit-debug-symbols", action="store_true")
    args = parser.parse_args()
    suffix = "-no-dsym" if args.omit_debug_symbols else ""
    output = ROOT / f"WebDriverAgent-17.0.2{suffix}-unsigned.ipa"
    result = prepare(ROOT / "WDA-17.0.2.zip", output,
                     omit_debug_symbols=args.omit_debug_symbols)
    (ROOT / f"wda-package{suffix}-manifest.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
