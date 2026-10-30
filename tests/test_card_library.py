import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIBRARY = ROOT / "library" / "india-cards.json"
REQUIRED = (
    "id",
    "name",
    "issuer",
    "segments",
    "joining_fee_inr",
    "annual_fee_inr",
    "fee_note",
    "rewards",
    "source_url",
    "fetched_on",
    "last_updated",
)


def test_card_library_entries_are_dated_and_sourced():
    payload = json.loads(LIBRARY.read_text(encoding="utf-8"))
    cards = payload["cards"]
    assert 10 <= len(cards) <= 25
    seen = set()
    for card in cards:
        for field in REQUIRED:
            assert card.get(field) not in (None, "", []), card["id"]
        assert card["id"] not in seen
        seen.add(card["id"])
        assert card["source_url"].startswith("https://")
        date.fromisoformat(card["fetched_on"])
        date.fromisoformat(card["last_updated"])
        assert card["fetched_on"] <= payload["fetched_on"]
    assert "Zepto" in payload["quick_commerce"]["not_named_as_of_fetched_on"]
    assert "Blinkit" in payload["quick_commerce"]["not_named_as_of_fetched_on"]
    ids = {card["id"] for card in cards}
    assert {"sbi-bpcl", "sbi-bpcl-octane", "kiwi-rupay", "rbl-play"} <= ids
    for offer in payload["platform_offers"]:
        assert offer["source_url"].startswith("https://")
        assert offer["platform"] == "District"
        date.fromisoformat(offer["fetched_on"])
        if offer["valid_until"]:
            date.fromisoformat(offer["valid_until"])
