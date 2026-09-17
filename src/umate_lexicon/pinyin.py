from __future__ import annotations

import re
import unicodedata

_TONE_VOWELS = {
    "a": "āáǎàa",
    "e": "ēéěèe",
    "i": "īíǐìi",
    "o": "ōóǒòo",
    "u": "ūúǔùu",
    "ü": "ǖǘǚǜü",
    "v": "ǖǘǚǜv",
}

_NUMBERED = re.compile(r"^([a-z:üv]+)([1-5])$", re.IGNORECASE)
_SYLLABLE_SPLIT = re.compile(r"\s+")


def normalize_cedict_syllable(raw: str) -> str:
    text = raw.strip().lower().replace("u:", "v")
    return text


def numbered_to_plain(numbered: str) -> str:
    parts = [_strip_tone_number(normalize_cedict_syllable(part)) for part in _SYLLABLE_SPLIT.split(numbered.strip()) if part]
    return " ".join(parts)


def numbered_to_toned(numbered: str) -> str:
    parts = [_apply_tone_number(normalize_cedict_syllable(part)) for part in _SYLLABLE_SPLIT.split(numbered.strip()) if part]
    return " ".join(parts)


def _strip_tone_number(syllable: str) -> str:
    match = _NUMBERED.match(syllable)
    if not match:
        return syllable.rstrip("12345")
    body = match.group(1).replace("ü", "v")
    return body


def _apply_tone_number(syllable: str) -> str:
    match = _NUMBERED.match(syllable)
    if not match:
        return syllable
    body, tone_s = match.group(1), match.group(2)
    tone = int(tone_s)
    if tone == 5:
        return body.replace("v", "ü")
    return _mark_tone(body, tone)


def _mark_tone(body: str, tone: int) -> str:
    lower = body.replace("v", "ü")
    # Standard placement: a/e, then ou, else last vowel.
    if "a" in lower:
        return _replace_vowel(lower, "a", tone)
    if "e" in lower:
        return _replace_vowel(lower, "e", tone)
    if "ou" in lower:
        return _replace_vowel(lower, "o", tone)
    for index in range(len(lower) - 1, -1, -1):
        ch = lower[index]
        if ch in _TONE_VOWELS:
            return lower[:index] + _TONE_VOWELS[ch][tone - 1] + lower[index + 1 :]
    return lower


def _replace_vowel(body: str, vowel: str, tone: int) -> str:
    index = body.index(vowel)
    return body[:index] + _TONE_VOWELS[vowel][tone - 1] + body[index + 1 :]


def parse_cedict_pinyin_field(field: str) -> tuple[str, str]:
    """Return (plain, toned) from a CEDICT [ni3 hao3] body without brackets."""
    numbered = field.strip()
    return numbered_to_plain(numbered), numbered_to_toned(numbered)


# Rime-style plain syllables. ü is v. Used to refuse leftover fragments
# such as zhon/zho and abbreviated codes such as nh.
PINYIN_SYLLABLES = frozenset(
    """
    a ai an ang ao
    ba bai ban bang bao bei ben beng bi bian biao bie bin bing bo bu
    ca cai can cang cao ce cei cen ceng ci cong cou cu cuan cui cun cuo
    cha chai chan chang chao che chen cheng chi chong chou chu chua chuai
    chuan chuang chui chun chuo
    da dai dan dang dao de dei den deng di dia dian diao die ding diu
    dong dou du duan dui dun duo
    e ei en eng er
    fa fan fang fei fen feng fiao fo fou fu
    ga gai gan gang gao ge gei gen geng gong gou gu gua guai guan guang
    gui gun guo
    ha hai han hang hao he hei hen heng hm hng hong hou hu hua huai huan
    huang hui hun huo
    ji jia jian jiang jiao jie jin jing jiong jiu ju juan jue jun
    ka kai kan kang kao ke kei ken keng kong kou ku kua kuai kuan kuang
    kui kun kuo
    la lai lan lang lao le lei leng li lia lian liang liao lie lin ling
    liu lo long lou lu luan lue lun luo lv lve
    m ma mai man mang mao me mei men meng mi mian miao mie min ming miu
    mo mou mu
    n na nai nan nang nao ne nei nen neng ng ni nian niang niao nie nin
    ning niu nong nou nu nuan nue nun nuo nv nve
    o ou
    pa pai pan pang pao pei pen peng pi pian piao pie pin ping po pou pu
    qi qia qian qiang qiao qie qin qing qiong qiu qu quan que qun
    ran rang rao re ren reng ri rong rou ru rua ruan rui run ruo
    sa sai san sang sao se sen seng si song sou su suan sui sun suo
    sha shai shan shang shao she shei shen sheng shi shou shu shua shuai
    shuan shuang shui shun shuo
    ta tai tan tang tao te tei teng ti tian tiao tie ting tong tou tu
    tuan tui tun tuo
    wa wai wan wang wei wen weng wo wu
    xi xia xian xiang xiao xie xin xing xiong xiu xu xuan xue xun
    ya yan yang yao ye yi yin ying yo yong you yu yuan yue yun
    za zai zan zang zao ze zei zen zeng zi zong zou zu zuan zui zun zuo
    zha zhai zhan zhang zhao zhe zhei zhen zheng zhi zhong zhou zhu zhua
    zhuai zhuan zhuang zhui zhun zhuo
    """.split()
)


def normalize_plain_pinyin(code: str) -> str:
    parts = [
        part.strip().lower().replace("u:", "v").replace("ü", "v")
        for part in _SYLLABLE_SPLIT.split(code.strip())
        if part.strip()
    ]
    return " ".join(parts)


def looks_like_pinyin(code: str) -> bool:
    parts = normalize_plain_pinyin(code).split()
    return bool(parts) and all(part in PINYIN_SYLLABLES for part in parts)


# Single-letter syllables other than a/o/e occupy the Rime prism and
# break QWERTY 简拼 (abbrev). Erhua must be attached (`hui r` → `huir`).
_ALLOWED_SINGLE = frozenset({"a", "o", "e"})
_SEP_RE = re.compile(r"[·•・,，、/;；]+")
_NON_CODE_RE = re.compile(r"[^a-zA-Z0-9 ]+")
_WS_RE = re.compile(r"\s+")


def sanitize_emit_code(code: str) -> str | None:
    """Return a Rime-safe plain code, or None if the row must be dropped.

    VoiMate Host compile assumes emit codes are already a–z / digits /
    spaces only. Keep this the single source of truth so the keyboard
    sync script does not rewrite lemma rows.
    """
    text = unicodedata.normalize("NFKD", code)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = _SEP_RE.sub(" ", text)
    text = _NON_CODE_RE.sub("", text)
    text = _WS_RE.sub(" ", text).strip().lower()
    if not text:
        return None
    toks = text.split()
    merged: list[str] = []
    for token in toks:
        if token == "r" and merged and re.fullmatch(r"[a-z]+", merged[-1]):
            merged[-1] = merged[-1] + "r"
        else:
            merged.append(token)
    toks = merged
    collapsed: list[str] = []
    run: list[str] = []

    def flush() -> None:
        nonlocal run
        if run:
            collapsed.append("".join(run))
            run = []

    for token in toks:
        if re.fullmatch(r"[a-z]", token):
            run.append(token)
        else:
            flush()
            collapsed.append(token)
    flush()
    toks = collapsed
    fixed: list[str] = []
    index = 0
    while index < len(toks):
        token = toks[index]
        if re.fullmatch(r"[a-z]", token) and token not in _ALLOWED_SINGLE:
            if fixed and re.fullmatch(r"[a-z0-9]+", fixed[-1]):
                fixed[-1] = fixed[-1] + token
            elif index + 1 < len(toks) and re.fullmatch(r"[a-z0-9]+", toks[index + 1]):
                toks[index + 1] = token + toks[index + 1]
            else:
                return None
        else:
            fixed.append(token)
        index += 1
    toks = fixed
    if not toks or not all(re.fullmatch(r"[a-z0-9]+", token) for token in toks):
        return None
    for token in toks:
        if len(token) == 1 and token.isalpha() and token not in _ALLOWED_SINGLE:
            return None
    return " ".join(toks)
