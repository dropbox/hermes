ALTER TABLE `labors` ADD `closing_fate_id` INT(11)  DEFAULT NULL AFTER `fate_id`;
ALTER TABLE `labors` ADD INDEX `ix_labors_closing_fate_id` (`closing_fate_id`);

UPDATE `labors` SET `closing_fate_id`=5;
ALTER TABLE `labors` ADD FOREIGN KEY (`closing_fate_id`) REFERENCES `fates` (`id`);
