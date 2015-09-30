ALTER TABLE `fates` ADD `for_owner` INT(1)  NOT NULL DEFAULT 1 AFTER `follows_id`;
ALTER TABLE `fates` ADD `for_creator` INT(1)  NOT NULL  DEFAULT 0 AFTER `follows_id`;
ALTER TABLE `labors` ADD `for_owner` INT(1)  NOT NULL DEFAULT 1 AFTER `host_id`;
ALTER TABLE `labors` ADD `for_creator` INT(1)  NOT NULL  DEFAULT 0 AFTER `host_id`;

UPDATE `fates` SET `for_owner`=0 where `id`=2;
UPDATE `fates` SET `for_creator`=1 where `id`=2;

UPDATE `labors` SET `for_owner`=1, `for_creator`=0 where `starting_labor_id` IS NULL;
UPDATE `labors` SET `for_owner`=0, `for_creator`=1 where `starting_labor_id` IS NOT NULL;
