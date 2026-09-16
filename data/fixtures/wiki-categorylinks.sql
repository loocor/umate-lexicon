-- Fixture categorylinks dump. Not a Wikimedia dump.
CREATE TABLE `categorylinks` (
  `cl_from` int,
  `cl_target_id` bigint,
  `cl_collation_id` smallint,
  `cl_sortkey` varbinary(230),
  `cl_timestamp` timestamp,
  `cl_sortkey_prefix` varbinary(255),
  `cl_type` enum('page','subcat','file')
);
INSERT INTO `categorylinks` VALUES (3,10,0,'MEITUAN','2026-09-01 00:00:00','','page'),(1,11,0,'KAIXIN','2026-09-01 00:00:00','','page');
