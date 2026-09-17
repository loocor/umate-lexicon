from pathlib import Path

from umate_lexicon.emit.aosp_en import emit_aosp_en, load_aosp_wordlist


def test_emit_aosp_en_writes_dict_and_unigrams(tmp_path: Path) -> None:
    csv_path = tmp_path / "words.csv"
    csv_path.write_text(
        "word=class,f=152\nword=type,f=147\nword=a,f=200\nword=hello,f=80\n",
        encoding="utf-8",
    )
    out = tmp_path / "rime"
    counts = emit_aosp_en(csv_path, out, min_length=4, unigram_limit=10)
    assert counts["aosp_en_words"] == 3
    assert counts["en_us_unigrams"] == 3
    body = (out / "aosp_en.dict.yaml").read_text(encoding="utf-8")
    assert "name: aosp_en" in body
    assert "class\tclass\t152" in body
    assert "\na\ta\t" not in body
    tsv = (out / "en_us_unigrams.tsv").read_text(encoding="utf-8")
    assert "class\t152" in tsv
    assert (out / "aosp_en.schema.yaml").is_file()
    words = load_aosp_wordlist(csv_path)
    assert words[0][0] == "a"
