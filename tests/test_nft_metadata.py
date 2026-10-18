import json

from PIL import Image

from src import nft_metadata

# The glider: period 4, travels diagonally, totalistic so no table needed.
GLIDER = {"rle": "x = 3, y = 3, rule = B3/S23\nbo$2bo$3o!", "rule": "B3/S23",
          "period": "4", "rarity": "common"}
CATALOG = {
    "xq4_153": dict(GLIDER, edition=None),   # demo ship, not a card
    "p4-02": dict(GLIDER, edition="2"),
    "p4-01": dict(GLIDER, edition="1"),
}
SITE = "https://example.com/automons/"


def test_cards_only_in_edition_order():
    ids = [sid for sid, _ in nft_metadata.deck_entries(CATALOG)]
    assert ids == ["p4-01", "p4-02"]


def test_metadata_points_at_the_site():
    meta = nft_metadata.metadata_for("p4-02", CATALOG["p4-02"], 2, SITE)
    assert meta["name"] == "Spaceship #2"
    assert meta["image"] == SITE + "nft/p4-02.gif"
    assert meta["external_url"].startswith(SITE + "#")
    traits = {a["trait_type"]: a["value"] for a in meta["attributes"]}
    assert traits["edition"] == "2 of 2"
    assert traits["ship"] == "p4-02"


def test_camera_follows_the_ship():
    frames = nft_metadata.flight_frames(GLIDER)
    assert len(frames) == 4
    # Every frame stays centred, so the gif loops in place instead of
    # the ship drifting out of the picture.
    for live in frames:
        xs = [x for x, _ in live]
        ys = [y for _, y in live]
        assert abs((min(xs) + max(xs)) / 2) <= 1
        assert abs((min(ys) + max(ys)) / 2) <= 1


def test_build_writes_json_and_gifs(tmp_path):
    n = nft_metadata.build(CATALOG, SITE, str(tmp_path))
    assert n == 2
    meta = json.loads((tmp_path / "p4-01.json").read_text())
    assert meta["properties"]["files"][0]["type"] == "image/gif"
    gif = Image.open(tmp_path / "p4-01.gif")
    assert gif.n_frames == 4
    assert gif.size == (nft_metadata.IMAGE_W, nft_metadata.IMAGE_H)
    assert json.loads((tmp_path / "collection.json").read_text())["name"] == "Spaceships"
