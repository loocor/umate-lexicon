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


def test_plain_syllable_inventory_rejects_fragments() -> None:
    from umate_lexicon.pinyin import looks_like_pinyin, normalize_plain_pinyin

    assert normalize_plain_pinyin("nü hao") == "nv hao"
    assert looks_like_pinyin("ni hao")
    assert looks_like_pinyin("zao")
    assert looks_like_pinyin("zhong")
    assert not looks_like_pinyin("nh")
    assert not looks_like_pinyin("ni3")
    assert not looks_like_pinyin("zhon")
    assert not looks_like_pinyin("zho")
