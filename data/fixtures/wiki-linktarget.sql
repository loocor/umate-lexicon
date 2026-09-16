-- Fixture linktarget dump. Not a Wikimedia dump.
CREATE TABLE `linktarget` (
  `lt_id` bigint,
  `lt_namespace` int,
  `lt_title` varbinary(255)
);
INSERT INTO `linktarget` VALUES (10,14,'中国公司'),(11,14,'2020年出生'),(12,0,'Ignored');
