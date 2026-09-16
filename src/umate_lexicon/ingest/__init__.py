from umate_lexicon.ingest.cedict import ingest_cedict
from umate_lexicon.ingest.chars import ingest_chars
from umate_lexicon.ingest.emoji import ingest_emoji
from umate_lexicon.ingest.essay import ingest_essay
from umate_lexicon.ingest.gold import ingest_gold
from umate_lexicon.ingest.luna import ingest_luna
from umate_lexicon.ingest.tencent import ingest_tencent
from umate_lexicon.ingest.tgh import ingest_tgh
from umate_lexicon.ingest.thuocl import ingest_thuocl
from umate_lexicon.ingest.unihan import ingest_unihan
from umate_lexicon.ingest.wiki import (
    ingest_wiki,
    ingest_wiki_category,
    ingest_wiki_linktarget,
    ingest_wiki_page,
)

__all__ = [
    "ingest_cedict",
    "ingest_chars",
    "ingest_emoji",
    "ingest_essay",
    "ingest_gold",
    "ingest_luna",
    "ingest_tencent",
    "ingest_tgh",
    "ingest_thuocl",
    "ingest_unihan",
    "ingest_wiki",
    "ingest_wiki_category",
    "ingest_wiki_linktarget",
    "ingest_wiki_page",
]
