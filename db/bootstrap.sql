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

INSERT INTO `fates` (`id`, `creation_type_id`, `completion_type_id`, `intermediate`, `description`)
VALUES
	(1,1,2, 0, 'A system that needs a reboot can be cleared by rebooting the machine.'),
	(2,3,4, 0, 'A system that needs maintenance made ready before maintenance can occur.'),
	(3,4,5, 1, 'Maintenance must be performed on a system that is prepped.');

UNLOCK TABLES;
