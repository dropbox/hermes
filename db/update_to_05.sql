ALTER TABLE `labors` ADD `fate_id` INT(11)  NOT NULL  DEFAULT 0 AFTER `host_id`;
ALTER TABLE `labors` DROP FOREIGN KEY `labors_ibfk_4`;

UPDATE `labors` SET `fate_id`=1;
ALTER TABLE `labors` ADD FOREIGN KEY `ix_fate_id` (`fate_id`) REFERENCES FATES(`id`);
