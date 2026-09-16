from pathlib import Path

from umate_lexicon.ingest.mysql_dump import iter_mysql_table_rows
from umate_lexicon.paths import data_dir


def test_fixture_page_dump_parses_redirect_flag() -> None:
    rows = list(iter_mysql_table_rows(data_dir() / "fixtures" / "wiki-page.sql", "page"))
    by_title = {row["page_title"]: row for row in rows}
    assert by_title["测试别名"]["page_is_redirect"] == 1
    assert by_title["美团公司"]["page_is_redirect"] == 0
    assert by_title["美团公司"]["page_len"] == 90


def test_escaped_string_and_null(tmp_path: Path) -> None:
    path = tmp_path / "page.sql"
    path.write_text(
        """
CREATE TABLE `page` (
  `page_id` int,
  `page_namespace` int,
  `page_title` varbinary(255),
  `page_is_redirect` tinyint,
  `page_len` int
);
INSERT INTO `page` VALUES (1,0,'O\\'Brien',0,NULL),(2,0,'A,B',1,12);
""",
        encoding="utf-8",
    )
    rows = list(iter_mysql_table_rows(path, "page"))
    assert rows[0]["page_title"] == "O'Brien"
    assert rows[0]["page_len"] is None
    assert rows[1]["page_title"] == "A,B"
    assert rows[1]["page_is_redirect"] == 1
