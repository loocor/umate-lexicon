import struct
import subprocess
import sys
from pathlib import Path

from umate_lexicon.enrich.category import classify
from umate_lexicon.ingest.chars import ingest_chars
from umate_lexicon.ingest.gold import ingest_gold
from umate_lexicon.ingest.tencent import ingest_tencent, parse_tencent_line
from umate_lexicon.layers import assign_layer
from umate_lexicon.lemma import Lemma, SourceRef
from umate_lexicon.paths import data_dir
from umate_lexicon.store import LemmaStore
from umate_lexicon.word2vec import iter_vocab_surfaces, write_vocab

_TENCENT = SourceRef("tencent", "cc-by-3.0-tencent", "tencent-light")
_WIKI = SourceRef("wiki", "cc-by-sa-wikimedia", "wiki")
_GOLD = SourceRef("gold", "umate-gold", "gold")


def write_word2vec_binary(path: Path, items: list[tuple[str, list[float]]]) -> None:
    if not items:
        raise ValueError("word2vec binary needs at least one vector")
    dim = len(items[0][1])
    with path.open("wb") as handle:
        handle.write(f"{len(items)} {dim}\n".encode("ascii"))
        for word, vector in items:
            handle.write(word.encode("utf-8"))
            handle.write(b" ")
            handle.write(struct.pack("<" + "f" * dim, *vector))
            handle.write(b"\n")


def test_parses_freq_and_embedding_lines() -> None:
    assert parse_tencent_line("微信\t100") == ("微信", 100)
    assert parse_tencent_line("人工智能 0.12 -0.03 0.44") == ("人工智能", 1)
    assert parse_tencent_line("xyz") == ("xyz", 1)


def test_covers_unique_han_and_overlays_gold_latin(tmp_path: Path) -> None:
    store = LemmaStore(tmp_path / "lemmas.sqlite")
    ingest_gold(store, data_dir() / "gold" / "product-terms.tsv")
    ingest_chars(store, data_dir() / "fixtures" / "chars.tsv")
    count = ingest_tencent(store, data_dir() / "fixtures" / "tencent.txt")
    assert count >= 2
    weixin = store.get("微信", "wei xin")
    assert weixin is not None
    assert weixin.domain_freq["tencent"] == 100
    ai = store.get("人工智能", "ren gong zhi neng")
    assert ai is not None
    assert ai.domain_freq["tencent"] == 1
    assert store.get("的", "de") is None or "tencent" not in (store.get("的", "de").domain_freq)
    vector = store.get("向量数据库", "xiang liang shu ju ku")
    assert vector is not None
    assert vector.status == "gold"
    assert vector.domain_freq["tencent"] == 3
    brand = store.get("umate", "umate")
    assert brand is not None
    assert brand.domain_freq["tencent"] == 8
    store.close()


def test_extracts_word2vec_binary_as_vocab_only(tmp_path: Path) -> None:
    source = tmp_path / "light_Tencent_AILab_ChineseEmbedding.bin"
    write_word2vec_binary(
        source,
        [
            ("微信", [0.12, -0.03, 0.44]),
            ("人工智能", [0.01, 0.02, 0.03]),
            ("银行卡", [-1.0, 0.0, 1.0]),
        ],
    )
    words = list(iter_vocab_surfaces(source))
    assert words == ["微信", "人工智能", "银行卡"]
    output = tmp_path / "tencent-light-vocab.txt"
    count = write_vocab(source, output)
    assert count == 3
    text = output.read_text(encoding="utf-8")
    assert text.splitlines() == words
    assert "0.12" not in text
    assert "3 3" not in text


def test_extract_keeps_text_first_column(tmp_path: Path) -> None:
    source = tmp_path / "tencent.txt"
    source.write_text("微信\t100\n人工智能 0.12 -0.03\n", encoding="utf-8")
    assert list(iter_vocab_surfaces(source)) == ["微信", "人工智能"]


def test_extract_script_reads_word2vec_binary(tmp_path: Path) -> None:
    source = tmp_path / "tiny.bin"
    write_word2vec_binary(source, [("微信", [0.5, 0.25]), ("银行卡", [0.0, 1.0])])
    output = tmp_path / "out.txt"
    script = Path(__file__).resolve().parents[1] / "scripts" / "extract-tencent-vocab.py"
    subprocess.check_call([sys.executable, str(script), str(source), "-o", str(output)])
    assert output.read_text(encoding="utf-8").splitlines() == ["微信", "银行卡"]


def test_tencent_only_bigram_stays_out_of_base() -> None:
    lemma = Lemma(
        surface="虚拟",
        pinyin_plain="xu ni",
        status="auto",
        sources=[_TENCENT],
    )
    assert assign_layer(lemma) == "bulk"


def test_tencent_only_four_char_stays_out_of_ext() -> None:
    lemma = Lemma(
        surface="人工智能",
        pinyin_plain="ren gong zhi neng",
        status="auto",
        sources=[_TENCENT],
    )
    assert assign_layer(lemma) == "bulk"


def test_tencent_overlay_keeps_gold_in_base() -> None:
    lemma = Lemma(
        surface="微信",
        pinyin_plain="wei xin",
        status="gold",
        flags=["gold"],
        sources=[_GOLD, _TENCENT],
    )
    assert assign_layer(lemma) == "base"


def test_wiki_plus_tencent_stays_bulk() -> None:
    lemma = Lemma(
        surface="开心",
        pinyin_plain="kai xin",
        status="auto",
        sources=[_WIKI, _TENCENT],
    )
    assert assign_layer(lemma) == "bulk"


def test_tencent_only_suffix_does_not_enter_orgs_or_places() -> None:
    company = classify(
        Lemma(
            surface="美团公司",
            pinyin_plain="mei tuan gong si",
            status="auto",
            sources=[_TENCENT],
        )
    )
    assert company.entity_type != "org"
    assert assign_layer(company) == "bulk"
    town = classify(
        Lemma(
            surface="一亩泉镇",
            pinyin_plain="yi mu quan zhen",
            status="auto",
            sources=[_TENCENT],
        )
    )
    assert town.entity_type != "place"
    assert assign_layer(town) == "bulk"


def test_ingest_tencent_only_lemma_is_not_base(tmp_path: Path) -> None:
    store = LemmaStore(tmp_path / "lemmas.sqlite")
    ingest_gold(store, data_dir() / "gold" / "product-terms.tsv")
    ingest_chars(store, data_dir() / "fixtures" / "chars.tsv")
    vocab = tmp_path / "tencent-light-vocab.txt"
    vocab.write_text("虚拟\n微信\n", encoding="utf-8")
    ingest_tencent(store, vocab)
    virtual = store.get("虚拟", "xu ni")
    assert virtual is not None
    assert {ref.source_id for ref in virtual.sources} == {"tencent"}
    assert assign_layer(classify(virtual)) == "bulk"
    weixin = store.get("微信", "wei xin")
    assert weixin is not None
    assert assign_layer(classify(weixin)) == "base"
    store.close()


def test_ingest_still_works_on_extracted_vocab_text(tmp_path: Path) -> None:
    store = LemmaStore(tmp_path / "lemmas.sqlite")
    ingest_gold(store, data_dir() / "gold" / "product-terms.tsv")
    ingest_chars(store, data_dir() / "fixtures" / "chars.tsv")
    vocab = tmp_path / "tencent-light-vocab.txt"
    vocab.write_text("微信\n人工智能\n", encoding="utf-8")
    count = ingest_tencent(store, vocab)
    assert count >= 2
    weixin = store.get("微信", "wei xin")
    assert weixin is not None
    assert weixin.domain_freq["tencent"] == 1
    ai = store.get("人工智能", "ren gong zhi neng")
    assert ai is not None
    assert ai.domain_freq["tencent"] == 1
    store.close()
