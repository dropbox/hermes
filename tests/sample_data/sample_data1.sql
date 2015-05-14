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

INSERT INTO event_types
VALUES
	(5,'system-shutdown','required','System shutdown required.');

INSERT INTO event_types
VALUES
	(6,'system-shutdown','complete','System shutdown complete.');

INSERT INTO fates
VALUES
	(1,1,2,'A system that needs a reboot can be cleared by rebooting the machine.');

INSERT INTO fates
VALUES
	(2,3,4,'A system that needs a maintenance must be attended to.');

INSERT INTO hosts
    VALUES (1, 'example.dropbox.com');

INSERT INTO hosts
    VALUES (2, 'sample.dropbox.com');

INSERT INTO hosts
    VALUES (3, 'test.dropbox.com');

INSERT INTO events
    VALUES (1, 1, "2015-04-31 10:00:00", "system", 1, "example.dropbox.com needs a reboot");

INSERT INTO events
    VALUES (2, 1, "2015-05-01 22:34:03", "system", 2, "example.dropbox.com rebooted.");
