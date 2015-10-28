TRUNCATE TABLE `fates`;
ALTER TABLE `fates` DROP FOREIGN KEY `fates_ibfk_2`;
ALTER TABLE `fates` DROP `completion_type_id`;

INSERT INTO fates
VALUES
	(1,1,NULL, 0, 1, 'Reboot or release the system.');

INSERT INTO fates
VALUES
	(2,2,1, 0, 1, 'A reboot finishes labors.');

INSERT INTO fates
VALUES
	(3,3,NULL, 0, 1, 'Release or acknowledge downtime');

INSERT INTO fates
VALUES
	(4,4,3, 0, 1, 'Perform maintenance');

INSERT INTO fates
VALUES
	(5,5,4, 1, 0, 'Maintenance completed');

ALTER TABLE `labors` ADD `fate_id` INT(11)  NOT NULL  DEFAULT 0 AFTER `starting_labor_id`;

UPDATE `labors` SET `fate_id`=1;
ALTER TABLE `labors` ADD FOREIGN KEY `ix_labors_fate_id` (`fate_id`) REFERENCES FATES(`id`);


UPDATE `labors` l
SET `fate_id` = (
  SELECT f.id
  FROM `events` e, `event_types` et, `fates` f
  WHERE l.creation_event_id = e.id AND e.event_type_id = et.id AND
        f.creation_type_id = et.id
);

INSERT INTO fates
VALUES
	(6,4,1, 0, 1, 'A release finishes labors');