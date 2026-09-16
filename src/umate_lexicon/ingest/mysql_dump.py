from __future__ import annotations

import gzip
from collections.abc import Iterator
from pathlib import Path
from typing import TextIO

_CREATE_PREFIX = "CREATE TABLE `"
_INSERT_PREFIX = "INSERT INTO `"


def open_sql_text(path: Path) -> TextIO:
    if path.name.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return path.open("r", encoding="utf-8-sig", errors="replace")


def preview_text(path: Path, limit: int = 4000) -> str:
    with open_sql_text(path) as handle:
        return handle.read(limit)


def iter_mysql_table_rows(path: Path, table: str) -> Iterator[dict[str, object]]:
    columns: list[str] = []
    with open_sql_text(path) as handle:
        for statement in _iter_statements(handle):
            stripped = statement.lstrip()
            upper = stripped.upper()
            if upper.startswith("CREATE TABLE"):
                name = _table_name(stripped, _CREATE_PREFIX)
                if name == table:
                    columns = _create_columns(stripped)
                continue
            if not upper.startswith("INSERT INTO"):
                continue
            name = _table_name(stripped, _INSERT_PREFIX)
            if name != table:
                continue
            if not columns:
                raise ValueError(f"INSERT for {table} before CREATE TABLE in {path}")
            payload = _insert_payload(stripped)
            for values in _iter_tuples(payload):
                if len(values) != len(columns):
                    raise ValueError(
                        f"{table} tuple width {len(values)} != {len(columns)} in {path}"
                    )
                yield dict(zip(columns, values, strict=True))


def _table_name(statement: str, prefix: str) -> str | None:
    idx = statement.find("`")
    if idx < 0:
        return None
    end = statement.find("`", idx + 1)
    if end < 0:
        return None
    return statement[idx + 1 : end]


def _insert_payload(statement: str) -> str:
    marker = " VALUES"
    idx = statement.upper().find(marker)
    if idx < 0:
        raise ValueError("INSERT without VALUES")
    payload = statement[idx + len(marker) :].lstrip()
    if payload.endswith(";"):
        payload = payload[:-1]
    return payload


def _create_columns(statement: str) -> list[str]:
    start = statement.find("(")
    end = statement.rfind(")")
    if start < 0 or end < 0 or end <= start:
        raise ValueError("CREATE TABLE without column list")
    columns: list[str] = []
    for raw in _split_top_level(statement[start + 1 : end]):
        item = raw.strip()
        if not item.startswith("`"):
            continue
        columns.append(item.split("`")[1])
    if not columns:
        raise ValueError("CREATE TABLE had no columns")
    return columns


def _iter_statements(handle: TextIO) -> Iterator[str]:
    leftover = ""
    in_string = False
    escape = False
    in_line_comment = False
    in_block_comment = False
    buf: list[str] = []
    eof = False
    while not eof:
        chunk = handle.read(1024 * 1024)
        if not chunk:
            src = leftover
            leftover = ""
            eof = True
            if not src:
                break
        else:
            src = leftover + chunk
            leftover = ""
        i = 0
        n = len(src)
        while i < n:
            if not eof and i == n - 1 and not in_string:
                leftover = src[i:]
                break
            ch = src[i]
            nxt = src[i + 1] if i + 1 < n else ""
            if in_line_comment:
                if ch == "\n":
                    in_line_comment = False
                    buf.append(ch)
                i += 1
                continue
            if in_block_comment:
                if ch == "*" and nxt == "/":
                    in_block_comment = False
                    i += 2
                else:
                    i += 1
                continue
            if in_string:
                buf.append(ch)
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == "'":
                    in_string = False
                i += 1
                continue
            if ch == "-" and nxt == "-":
                in_line_comment = True
                i += 2
                continue
            if ch == "/" and nxt == "*":
                in_block_comment = True
                i += 2
                continue
            if ch == "'":
                in_string = True
                buf.append(ch)
                i += 1
                continue
            if ch == ";":
                stmt = "".join(buf).strip()
                buf = []
                if stmt:
                    yield stmt
                i += 1
                continue
            buf.append(ch)
            i += 1
    tail = "".join(buf).strip()
    if tail:
        yield tail


def _iter_tuples(payload: str) -> Iterator[tuple[object, ...]]:
    i = 0
    n = len(payload)
    while i < n:
        while i < n and payload[i] in " \t\r\n,":
            i += 1
        if i >= n:
            return
        if payload[i] != "(":
            raise ValueError(f"expected tuple at index {i}")
        i += 1
        row: list[object] = []
        while True:
            while i < n and payload[i] in " \t":
                i += 1
            if i >= n:
                raise ValueError("unterminated tuple")
            if payload[i] == "'":
                value, i = _parse_string(payload, i)
                row.append(value)
            elif payload.startswith("NULL", i) and (i + 4 == n or payload[i + 4] in ",)"):
                row.append(None)
                i += 4
            else:
                j = i
                while j < n and payload[j] not in ",)":
                    j += 1
                row.append(_parse_scalar(payload[i:j].strip()))
                i = j
            while i < n and payload[i] in " \t":
                i += 1
            if i < n and payload[i] == ",":
                i += 1
                continue
            if i < n and payload[i] == ")":
                i += 1
                yield tuple(row)
                break
            raise ValueError("expected comma or closing parenthesis")


def _parse_string(payload: str, i: int) -> tuple[str, int]:
    i += 1
    out: list[str] = []
    n = len(payload)
    while i < n:
        ch = payload[i]
        if ch == "\\" and i + 1 < n:
            nxt = payload[i + 1]
            mapping = {
                "n": "\n",
                "r": "\r",
                "t": "\t",
                "0": "\0",
                "\\": "\\",
                "'": "'",
                '"': '"',
                "b": "\b",
                "Z": "\x1a",
            }
            out.append(mapping.get(nxt, nxt))
            i += 2
            continue
        if ch == "'":
            if i + 1 < n and payload[i + 1] == "'":
                out.append("'")
                i += 2
                continue
            return "".join(out), i + 1
        out.append(ch)
        i += 1
    raise ValueError("unterminated string")


def _parse_scalar(token: str) -> object:
    if token == "":
        return None
    if token.startswith("0x") or token.startswith("0X"):
        return bytes.fromhex(token[2:])
    try:
        if "." in token or "e" in token.lower():
            return float(token)
        return int(token)
    except ValueError:
        return token


def _split_top_level(body: str) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    depth = 0
    in_string = False
    escape = False
    for ch in body:
        if in_string:
            buf.append(ch)
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == "'":
                in_string = False
            continue
        if ch == "'":
            in_string = True
            buf.append(ch)
            continue
        if ch == "(":
            depth += 1
            buf.append(ch)
            continue
        if ch == ")":
            depth -= 1
            buf.append(ch)
            continue
        if ch == "," and depth == 0:
            parts.append("".join(buf))
            buf = []
            continue
        buf.append(ch)
    if buf:
        parts.append("".join(buf))
    return parts
