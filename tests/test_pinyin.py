from umate_lexicon.pinyin import numbered_to_plain, numbered_to_toned, parse_cedict_pinyin_field


def test_cedict_numbered_plain() -> None:
    plain, toned = parse_cedict_pinyin_field("chong2 qing4")
    assert plain == "chong qing"
    assert "ó" in toned or "ò" in toned


def test_nu_colon_becomes_v() -> None:
    assert numbered_to_plain("nu:3") == "nv"


def test_neutral_tone() -> None:
    assert numbered_to_plain("ne5") == "ne"
    assert numbered_to_toned("ne5") == "ne"
