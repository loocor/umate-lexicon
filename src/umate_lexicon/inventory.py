from __future__ import annotations

from collections import Counter

from umate_lexicon.layers import assign_layer, emit_weight, han_len
from umate_lexicon.store import LemmaStore

PROBES: dict[str, tuple[str, ...]] = {
    "core": ("的", "你好", "我", "是", "银行"),
    "product": ("微信", "抖音", "小红书", "美团", "哔哩哔哩", "字节跳动", "umate"),
    "ai_zh": (
        "大模型",
        "大语言模型",
        "提示词",
        "提示工程",
        "多模态",
        "向量库",
        "向量数据库",
        "检索增强",
        "人工智能",
        "智能体",
        "微调",
        "幻觉",
        "上下文",
    ),
    "ai_latin": ("llm", "rag", "mcp", "openai", "ChatGPT", "Python", "GPU"),
    "it": ("编程", "数据库", "服务器", "开源", "云原生", "区块链"),
    "geo": ("北京", "上海", "重庆", "昆明", "新疆", "香港"),
    "history": ("李白", "孔子", "秦始皇", "曹雪芹", "鲁迅"),
    "names_mod": ("马云", "马化腾", "雷军", "马斯克"),
    "emoji": ("哈哈", "笑哭", "好的", "点赞"),
}


def summarize_store(store: LemmaStore) -> dict[str, object]:
    layers: Counter[str] = Counter()
    licenses: Counter[str] = Counter()
    sources: Counter[str] = Counter()
    han_buckets: Counter[str] = Counter()
    status: Counter[str] = Counter()
    surfaces: set[str] = set()
    for lemma in store.all_lemmas():
        layer = assign_layer(lemma) or "dropped"
        layers[layer] += 1
        status[lemma.status] += 1
        surfaces.add(lemma.surface)
        n = han_len(lemma.surface)
        if n == 0:
            han_buckets["latin_or_other"] += 1
        elif n == 1:
            han_buckets["1"] += 1
        elif n in {2, 3}:
            han_buckets["2-3"] += 1
        elif n == 4:
            han_buckets["4"] += 1
        else:
            han_buckets["5+"] += 1
        for ref in lemma.sources:
            licenses[ref.license] += 1
            sources[ref.source_id] += 1
    probes: dict[str, dict[str, object]] = {}
    for group, names in PROBES.items():
        rows = []
        for surface in names:
            lemmas = [item for item in store.readings_for(surface) if item.status != "rejected"]
            if not lemmas:
                rows.append({"surface": surface, "present": False})
                continue
            best = max(lemmas, key=lambda item: (emit_weight(item), item.status == "gold"))
            rows.append(
                {
                    "surface": surface,
                    "present": True,
                    "status": best.status,
                    "pinyin": best.pinyin_plain,
                    "layer": assign_layer(best),
                    "weight": emit_weight(best),
                    "freq": dict(best.domain_freq),
                }
            )
        probes[group] = {
            "hit": sum(1 for row in rows if row["present"]),
            "total": len(rows),
            "rows": rows,
        }
    return {
        "lemmas": store.count(),
        "surfaces": len(surfaces),
        "layers": dict(layers),
        "status": dict(status),
        "han": dict(han_buckets),
        "licenses": dict(licenses),
        "sources": dict(sources),
        "probes": probes,
    }


def render_summary(summary: dict[str, object]) -> str:
    lines = [
        f"lemmas\t{summary['lemmas']}",
        f"surfaces\t{summary['surfaces']}",
        "layer\tcount",
    ]
    layers = summary["layers"]
    assert isinstance(layers, dict)
    for key, value in sorted(layers.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"{key}\t{value}")
    lines.append("source\tcount")
    sources = summary["sources"]
    assert isinstance(sources, dict)
    for key, value in sorted(sources.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"{key}\t{value}")
    lines.append("probe\tsurface\tpresent\tstatus\tlayer\tweight")
    probes = summary["probes"]
    assert isinstance(probes, dict)
    for group, payload in probes.items():
        assert isinstance(payload, dict)
        for row in payload["rows"]:
            lines.append(
                "\t".join(
                    [
                        group,
                        str(row["surface"]),
                        "yes" if row["present"] else "no",
                        str(row.get("status", "")),
                        str(row.get("layer", "")),
                        str(row.get("weight", "")),
                    ]
                )
            )
    return "\n".join(lines) + "\n"
