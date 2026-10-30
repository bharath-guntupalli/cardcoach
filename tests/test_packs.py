import zipfile
from pathlib import Path

import packs.build_packs as build_packs

ROOT = Path(__file__).resolve().parents[1]


def test_packs_stay_within_platform_limits():
    build_packs.main()
    canon = (ROOT / "canon" / "CARDCOACH.md").read_bytes()
    copies = [
        ROOT / "packs" / "claude" / "cardcoach" / "references" / "CARDCOACH.md",
        ROOT / "packs" / "gemini" / "cardcoach" / "references" / "CARDCOACH.md",
        ROOT / ".cursor" / "skills" / "cardcoach" / "references" / "CARDCOACH.md",
        ROOT / "packs" / "chatgpt" / "knowledge" / "CARDCOACH.md",
        ROOT / "dist" / "chatgpt" / "CARDCOACH.md",
    ]
    for path in copies:
        assert path.read_bytes() == canon

    engine = (ROOT / "src" / "cardcoach" / "engine.py").read_bytes()
    assert (ROOT / "packs" / "chatgpt" / "knowledge" / "cardcoach_audit.py").read_bytes() == engine
    assert (ROOT / "dist" / "chatgpt" / "cardcoach_audit.py").read_bytes() == engine
    cards = (ROOT / "library" / "india-cards.json").read_bytes()
    assert (ROOT / "packs" / "claude" / "cardcoach" / "references" / "india-cards.json").read_bytes() == cards
    assert (ROOT / "dist" / "chatgpt" / "india-cards.json").read_bytes() == cards

    instructions = (ROOT / "packs" / "chatgpt" / "PROJECT_INSTRUCTIONS.md").read_text(encoding="utf-8")
    assert len(instructions) <= 6000
    gem = (ROOT / "packs" / "gemini" / "GEM_INSTRUCTIONS.txt").read_text(encoding="utf-8")
    assert len(gem) <= 1000

    for skill in (
        ROOT / "packs" / "claude" / "cardcoach",
        ROOT / "packs" / "gemini" / "cardcoach",
        ROOT / ".cursor" / "skills" / "cardcoach",
    ):
        assert skill.name == "cardcoach"
        text = (skill / "SKILL.md").read_text(encoding="utf-8")
        assert text.startswith("---\nname: cardcoach\n")
        description = text.split("description: ", 1)[1].split("\n---", 1)[0]
        assert len(description) <= 1024
        lowered = description.lower()
        assert "claude" not in lowered
        assert "anthropic" not in lowered
        assert len(text.splitlines()) < 500

    for archive_name in ("cardcoach-claude.zip", "cardcoach-gemini.zip"):
        with zipfile.ZipFile(ROOT / "dist" / archive_name) as archive:
            names = archive.namelist()
        assert "cardcoach/SKILL.md" in names
        assert "cardcoach/references/india-cards.json" in names
        assert all(name.startswith("cardcoach/") for name in names)
