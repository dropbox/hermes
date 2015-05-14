INSERT INTO event_types
VALUES
	(1,'system-reboot','required','This system requires a reboot.');

INSERT INTO event_types
VALUES
	(2,'system-reboot','completed','This system rebooted.');

INSERT INTO event_types
VALUES
	(3,'system-maintenance','required','This system requires maintenance.');

INSERT INTO event_types
VALUES
	(4,'system-maintenance','completed','System maintenance completed.');

INSERT INTO fates
VALUES
	(1,1,2,'A system that needs a reboot can be cleared by rebooting the machine.');
