# Dump of table event_types
# ------------------------------------------------------------

LOCK TABLES `event_types` WRITE;

INSERT INTO `event_types` (`id`, `category`, `state`, `description`)
VALUES
	(1,'system-reboot','required','This system requires a reboot.'),
	(2,'system-reboot','completed','This system rebooted.'),
	(3,'system-maintenance','required','This system requires maintenance.'),
	(4,'system-maintenance','ready','This system is ready for maintenance.'),
	(5,'system-maintenance','completed','System maintenance completed.');

UNLOCK TABLES;

# Dump of table fates
# ------------------------------------------------------------

LOCK TABLES `fates` WRITE;

INSERT INTO `fates` (`id`, `creation_type_id`, `completion_type_id`, `follows_id`, `for_creator`, `for_owner`, `description`)
VALUES
    (1, 1, 2, NULL, 0, 1, 'A system that needs a reboot can be cleared by rebooting the machine.'),
    (2, 3, 4, NULL, 0, 1, 'System must be released using \"cloudbox release\" so maintenance can be carried out.'),
    (3, 4, 5, 2, 1, 0, 'Maintenance must be performed on a system that is prepped.'),
    (4, 1, 4, NULL, 0, 1, 'A system that needs a reboot can also just be released.');


UNLOCK TABLES;
