-- Fixture page dump. Not a Wikimedia dump.
CREATE TABLE `page` (
  `page_id` int,
  `page_namespace` int,
  `page_title` varbinary(255),
  `page_is_redirect` tinyint,
  `page_is_new` tinyint,
  `page_random` float,
  `page_touched` binary(14),
  `page_links_updated` varbinary(14),
  `page_latest` int,
  `page_len` int,
  `page_content_model` varbinary(32),
  `page_lang` varbinary(35)
);
INSERT INTO `page` VALUES (1,0,'开心',0,0,0.1,'20260901000000',NULL,1,100,'wikitext',NULL),(2,0,'文件备份',0,0,0.1,'20260901000000',NULL,2,80,'wikitext',NULL),(3,0,'美团公司',0,0,0.1,'20260901000000',NULL,3,90,'wikitext',NULL),(4,0,'测试别名',1,0,0.1,'20260901000000',NULL,4,10,'wikitext',NULL),(5,0,'一剑镇神州',0,0,0.1,'20260901000000',NULL,5,200,'wikitext',NULL);
