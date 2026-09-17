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


def test_sanitize_emit_code_merges_erhua_and_collapses_letters() -> None:
    from umate_lexicon.pinyin import sanitize_emit_code

    assert sanitize_emit_code("yi hui r") == "yi huir"
    assert sanitize_emit_code("q q") == "qq"
    assert sanitize_emit_code("b zhan") == "bzhan"
    assert sanitize_emit_code("ni hao") == "ni hao"
    assert sanitize_emit_code("nǐ hǎo") == "ni hao"
    assert sanitize_emit_code("fen·se") == "fen se"
    assert sanitize_emit_code("") is None
    # lone letter other than a/o/e cannot stand as a syllable
    assert sanitize_emit_code("q") is None
