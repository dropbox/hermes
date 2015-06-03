import ipaddress
import logging
from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError


from .util import ApiHandler, PluginHelper
from .. import exc
from ..models import Host, EventType, Event, Labor, Fate, Quest
from ..util import qp_to_bool as qpbool, parse_set_query

from datetime import datetime
from dateutil import parser


log = logging.getLogger(__name__)


class HostsHandler(ApiHandler):

    def post(self):
        """ Create a Host entry

        Example Request:


            POST /api/v1/hosts HTTP/1.1
            Host: localhost
            Content-Type: application/json
            {
                "hostname": "example"
            }

            or:

            {
                "hosts": [
                    {
                        "hostname": "server1"
                    },
                    {
                        "hostname": "server2"
                    },
                    ...
                ]
            }

        Example response:

            HTTP/1.1 201 OK
            Location: /api/v1/hosts/example

            {
                "status": "created",
                "href": "/api/v1/hosts/example",
                "id": 1,
                "hostname": "example"
            }

            or:

            {
                "status": "created",
                "hosts":
                [
                    {
                        "href": "/api/v1/hosts/testserver1",
                        "hostname": "testserver1",
                        "id": 42
                    },
                    {
                        "href": "/api/v1/hosts/testserver2",
                        "hostname": "testserver2",
                        "id": 43
                    },
                    {
                        "href": "/api/v1/hosts/testserver3",
                        "hostname": "testserver3",
                        "id": 44
                    }
                ],
                "totalHosts": 3
            }
        """

        try:
            if "hosts" in self.jbody:
                hostnames = self.jbody["hosts"]
            else:
                hostnames = [{"hostname": self.jbody["hostname"]}]
        except KeyError as err:
            raise exc.BadRequest(
                "Missing Required Argument: {}".format(err.message)
            )
        except ValueError as err:
            raise exc.BadRequest(err.message)

        try:
            hosts = []
            for hostname in hostnames:
                host = Host.create(self.session, hostname["hostname"])
                hosts.append(host.to_dict("/api/v1"))
        except IntegrityError as err:
            raise exc.Conflict(err.orig.message)
        except exc.ValidationError as err:
            raise exc.BadRequest(err.message)

        self.session.commit()

        if len(hosts) == 1:
            json = hosts[0]
            self.created("/api/v1/hosts/{}".format(hosts[0]["hostname"]), json)
        else:
            self.created(data={"hosts": hosts, "totalHosts": len(hosts)})

    def get(self):
        """ Get all Hosts

        Example Request:

            GET /api/v1/hosts HTTP/1.1
            Host: localhost

        Example response:

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "status": "ok",
                "hosts": [
                    {
                        "id": 1,
                        "href": "/api/v1/hosts/server1",
                        "hostname": "server1",
                    },
                    ...
                ],
                "limit": 10,
                "offset": 0,
                "totalHosts": 1,
            }
        """
        hostname = self.get_argument("hostname", None)

        hosts = self.session.query(Host)
        if hostname is not None:
            hosts = hosts.filter_by(hostname=hostname)

        offset, limit, expand = self.get_pagination_values()
        hosts, total = self.paginate_query(hosts, offset, limit)

        json = {
            "limit": limit,
            "offset": offset,
            "totalHosts": total,
            "hosts": [host.to_dict("/api/v1") for host in hosts.all()],
        }

        self.success(json)


class HostHandler(ApiHandler):
    def get(self, hostname):
        """Get a specific Host

        Example Request:

            GET /api/v1/hosts/example HTTP/1.1
            Host: localhost

        Example response:

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "status": "ok",
                "id": 1,
                "hostname": "example",
                "labors": [],
                "quests": [],
                "events": [],
                "href": "/api/v1/hosts/example",
                "limit": 10,
                "offset": 0,
                "lastEvent": "2015-05-05 22:13:11"
            }

        Args:
            hostname: the name of the host to get
        """
        offset, limit, expand = self.get_pagination_values()
        host = self.session.query(Host).filter_by(hostname=hostname).scalar()
        if not host:
            raise exc.NotFound("No such Host {} found".format(hostname))

        json = host.to_dict("/api/v1")
        json["limit"] = limit
        json["offset"] = offset

        # add the labors and quests
        labors = []
        quests = []
        for labor in (
                host.get_labors().limit(limit).offset(offset)
                .from_self().order_by(Labor.creation_time).all()
        ):
            if "labors" in expand:
                labor_json = labor.to_dict("/api/v1")
                if "events" in expand:
                    labor_json["creationEvent"] = (
                        labor.creation_event.to_dict("/api/v1")
                    )
                    if "eventtypes" in expand:
                        labor_json["creationEvent"]["eventType"] = (
                            labor.creation_event.event_type.to_dict("/api/v1")
                        )
                labors.append(labor_json)
            else:
                labors.append({"id": labor.id, "href": labor.href("/api/v1")})

            if labor.quest and "quests" in expand:
                quests.append(labor.quest.to_dict("/api/v1"))
            elif labor.quest:
                quests.append(
                    {
                        "id": labor.quest.id,
                        "href": labor.quest.href("/api/v1")
                    }
                )
        json["labors"] = labors
        json["quests"] = quests

        # add the events
        events = []
        last_event = host.get_latest_events().first()
        for event in (
                host.get_latest_events().limit(limit).offset(offset)
                .from_self().order_by(Event.timestamp).all()
        ):
            if "events" in expand:
                event_json = event.to_dict("/api/v1")
                if "eventtypes" in expand:
                    event_json["eventType"] = (
                        event.event_type.to_dict("/api/v1")
                    )
                events.append(event_json)
            else:
                events.append({
                    "id": event.id, "href": event.href("/api/v1")
                })

        if last_event:
            json["lastEvent"] = str(last_event.timestamp)
        else:
            json["lastEvent"] = None
        json["events"] = events

        self.success(json)

    def put(self, hostname):
        """Update a Host

        Example Request:

            PUT /api/v1/hosts/example HTTP/1.1
            Host: localhost
            Content-Type: application/json
            X-NSoT-Email: user@localhost

            {
                "hostname": "newname",
            }

        Example response:

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "status": "ok",
                "id": 1,
                "href": "/api/v1/hosts/example",
                "hostname": "newname",
            }

        Args:
            hostname: the hostname to update
        """
        host = self.session.query(Host).filter_by(hostname=hostname).scalar()
        if not host:
            raise exc.NotFound("No such Host {} found".format(hostname))

        try:
            new_hostname = self.jbody["hostname"]
        except KeyError as err:
            raise exc.BadRequest("Missing Required Argument: {}".format(err.message))

        try:
            host = host.update(
                hostname=new_hostname,
            )
        except IntegrityError as err:
            raise exc.Conflict(str(err.orig))

        json = host.to_dict("/api/v1")

        self.success(json)

    def delete(self, hostname):
        """Delete a Host

        Not supported
        """
        self.not_supported()


class EventTypesHandler(ApiHandler):

    def post(self):
        """ Create a EventType entry

        Example Request:


            POST /api/v1/eventtypes HTTP/1.1
            Host: localhost
            Content-Type: application/json
            {
                "category": "system-reboot",
                "state": "required",
                "description": "System requires a reboot.",
            }

            or:

            {
                "eventTypes": [
                    {
                        "category": "foo",
                        "state": "bar",
                        "description": "Some description"

                    },
                    {
                        "category": "foo",
                        "state": "baz",
                        "description": "Some description"
                    },
                    {
                        "category": "tango",
                        "state": "foxtrot",
                        "description": "Some description"
                    }
                ]
            }

        Example response:

            HTTP/1.1 201 OK
            Location: /api/v1/eventtypes/1

            {
                "status": "created",
                "id": 1,
                "category": "system-reboot",
                "state": "required",
                "description": "System requires a reboot.",
            }

            or:

            {
                "status": "created",
                "eventTypes":
                [
                    {
                        "category": "foo",
                        "state": "bar",
                        "href": "/api/v1/eventtypes/7",
                        "id": 7,
                        "description": "Some description"
                    },
                    {
                        "category": "foo",
                        "state": "baz",
                        "href": "/api/v1/eventtypes/8",
                        "id": 8,
                        "description": "Some description"
                    },
                    {
                        "category": "tango",
                        "state": "foxtrot",
                        "href": "/api/v1/eventtypes/9",
                        "id": 9,
                        "description": "Some description"
                    }
                ],
                "totalEventTypes": 3
            }

        """

        try:
            if "eventTypes" in self.jbody:
                event_types = self.jbody["eventTypes"]
            else:
                event_types = [
                    {
                        "category": self.jbody["category"],
                        "state": self.jbody["state"],
                        "description": self.jbody["description"]
                    }
                ]

        except KeyError as err:
            raise exc.BadRequest("Missing Required Argument: {}".format(err.message))
        except ValueError as err:
            raise exc.BadRequest(err.message)

        try:
            created_types = []
            for x in range(0, len(event_types)):
                created_type = EventType.create(
                    self.session, event_types[x]["category"],
                    event_types[x]["state"],
                    description=event_types[x]["description"]
                )
                created_types.append(created_type.to_dict("/api/v1"))
        except IntegrityError as err:
            if "Duplicate" in err.message:
                raise exc.Conflict("Cannot create duplicate event type")
            else:
                raise exc.Conflict(err.message)
        except exc.ValidationError as err:
            raise exc.BadRequest(err.message)

        self.session.commit()

        if len(created_types) == 1:
            json = created_types[0]
            self.created(
                "/api/v1/eventtypes/{}".format(created_types[0]["id"]), json
            )
        else:
            self.created(
                data={
                    "eventTypes": created_types,
                    "totalEventTypes": len(event_types)
                }
            )

    def get(self):
        """ Get all EventTypes

        Example Request:

            GET /api/v1/eventtypes HTTP/1.1
            Host: localhost

        Example response:

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "status": "ok",
                limit: int,
                offset: int,
                totalEventTypes: int,
                eventTypes: [
                    {
                        id: int,
                        category: string,
                        state: string,
                        description: string,
                    },
                    ...
                ],
            }
        """
        category = self.get_argument("category", None)
        state = self.get_argument("state", None)

        event_types = self.session.query(EventType)
        if category is not None:
            event_types = event_types.filter_by(category=category)

        if state is not None:
            event_types = event_types.filter_by(state=state)

        offset, limit, expand = self.get_pagination_values()
        event_types, total = self.paginate_query(event_types, offset, limit)

        json = {
            "limit": limit,
            "offset": offset,
            "totalEventTypes": total,
            "eventTypes": (
                [event_type.to_dict("/api/v1") for event_type in event_types.all()]
            ),
        }

        self.success(json)


class EventTypeHandler(ApiHandler):
    def get(self, id):
        """Get a specific EventType

        Example Request:

            GET /api/v1/eventtypes/1/ HTTP/1.1
            Host: localhost

        Example response:

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "status": "ok",
                "id": 1,
                "category": "system-reboot",
                "state": "required",
                "description": "This system requires a reboot",
                "events": [],
                "fates": [],
            }

        Args:
            id: the id of the EventType
        """
        offset, limit, expand = self.get_pagination_values()
        event_type = (
            self.session.query(EventType).filter_by(id=id).scalar()
        )
        if not event_type:
            raise exc.NotFound("No such EventType {} found".format(id))

        json = event_type.to_dict("/api/v1")
        json["limit"] = limit
        json["offset"] = offset

        # add the events
        events = []
        for event in (
                event_type.get_latest_events().limit(limit).offset(offset)
                .from_self().order_by(Event.timestamp).all()
        ):
            if "events" in expand:
                events.append(event.to_dict("/api/v1"))
            else:
                events.append({
                    "id": event.id, "href": event.href("/api/v1")
                })
        json["events"] = events

        # add the associated fates
        fates = []
        for fate in (
            event_type.get_associated_fates().all()
        ):
            if "fates" in expand:
                fates.append(fate.to_dict("/api/v1"))
            else:
                fates.append({
                    "id": fate.id, "href": fate.href("/api/v1")
                })
        json["fates"] = fates

        self.success(json)

    def put(self, id):
        """Update an EventType

        Example Request:

            PUT /api/v1/eventtypes/1/ HTTP/1.1
            Host: localhost
            Content-Type: application/json
            X-NSoT-Email: user@localhost

            {
                "description": "New description",
            }

        Example response:

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "status": "ok",
                "id": 1,
                "category": "system-reboot",
                "state": "required",
                "description": "New description",
            }

        Args:
            id: the id of the Event Type
        """
        event_type = (
            self.session.query(EventType).filter_by(id=id).scalar()
        )
        if not event_type:
            raise exc.NotFound("No such EventType {} found".format(id))

        try:
            description = self.jbody["description"]
        except KeyError as err:
            raise exc.BadRequest("Missing Required Argument: {}".format(err.message))

        try:
            event_type.update(
                description=description,
            )
        except IntegrityError as err:
            raise exc.Conflict(str(err.orig))

        json = event_type.to_dict("/api/v1")

        self.success(json)

    def delete(self, id):
        """Delete an EventType

        Not supported
        """
        self.not_supported()


class EventsHandler(ApiHandler):

    def post(self):
        """ Create an Event entry

        Example Request:

            POST /api/v1/events HTTP/1.1
            Host: localhost
            Content-Type: application/json
            {
                "hostname": "example",
                "user": "johnny",
                "eventTypeId": 3,
                "note": "Sample description"
            }

        Example response:

            HTTP/1.1 201 OK
            Location: /api/v1/events/1

            {
                "status": "ok",
                "data": {
                    "event": {
                        "id": 1,
                        "hostname": "example",
                        "user": "johnny",
                        "eventTypeId": 3,
                        "note": "Sample description"
                    }
                }
            }
        """

        try:
            hostname = self.jbody["hostname"]
            user = self.jbody["user"]
            event_type_id = self.jbody["eventTypeId"]
            note = self.jbody["note"]
        except KeyError as err:
            raise exc.BadRequest("Missing Required Argument: {}".format(err.message))
        except ValueError as err:
            raise exc.BadRequest(err.message)

        event_type = self.session.query(EventType).get(event_type_id)

        if event_type is None:
            self.write_error(400, message="Bad event type")
            return

        host = Host.get_host(self.session, hostname)

        if host is None:
            host = Host.create(self.session, hostname)

        try:
            event = Event.create(
                self.session, host, user, event_type, note=note
            )
        except IntegrityError as err:
            raise exc.Conflict(err.orig.message)
        except exc.ValidationError as err:
            raise exc.BadRequest(err.message)

        self.session.commit()

        json = event.to_dict("/api/v1")
        json["href"] = "/api/v1/events/{}".format(event.id)

        self.created("/api/v1/events/{}".format(event.id), json)

    def get(self):
        """ Get all Events

        Example Request:

            GET /api/v1/events HTTP/1.1
            Host: localhost

        Example response:

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                status: ok
                limit: int,
                page: int,
                totalEvents: int,
                events: [
                    {
                        id: int,
                        hostId: int,
                        timestamp: timestamp,
                        user: string,
                        eventTypeId: int,
                        note: string,
                    },
                    ...
                ],
            }
        """
        events = self.session.query(Event).order_by(desc(Event.timestamp))

        offset, limit, expand = self.get_pagination_values()
        events, total = self.paginate_query(events, offset, limit)

        events = events.from_self().order_by(Event.timestamp)

        json = {
            "limit": limit,
            "offset": offset,
            "totalEvents": total,
            "events": [event.to_dict("/api/v1") for event in events.all()],
        }

        self.success(json)


class EventHandler(ApiHandler):
    def get(self, id):
        """Get a specific Event

        Example Request:

            GET /api/v1/events/1/ HTTP/1.1
            Host: localhost

        Example response:

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "status": "ok",
                 id: int,
                 hostId: int,
                 timestamp: timestamp,
                 user: string,
                 eventTypeId: int,
                 note: string,
            }

        Args:
            id: the id of the event to get
        """
        offset, limit, expand = self.get_pagination_values()
        event = self.session.query(Event).filter_by(id=id).scalar()
        if not event:
            raise exc.NotFound("No such Event {} found".format(id))

        json = event.to_dict("/api/v1")

        if "hosts" in expand:
            json["host"] = event.host.to_dict("/api/v1")

        if "eventtypes" in expand:
            json["eventType"] = event.event_type.to_dict("/api/v1")

        self.success(json)

    def put(self, id):
        """Update an Event

        Not supported
        """
        self.not_supported()

    def delete(self, id):
        """Delete an Event

        Not supported
        """
        self.not_supported()


class FatesHandler(ApiHandler):

    def post(self):
        """ Create a Fate entry

        Example Request:


            POST /api/v1/fates HTTP/1.1
            Host: localhost
            Content-Type: application/json
            {
                creationEventTypeId: 1,
                completionEventTypeId: 2,
                intermediate: false,
                description: "This is a fate"
            }

        Example response:

            HTTP/1.1 201 OK
            Location: /api/v1/hosts/example

            {
                "status": "created",
                creationEventTypeId: 1,
                completionEventTypeId: 2,
                intermediate: false,
                description: "This is a fate"
            }
        """

        try:
            creation_event_type_id = self.jbody["creationEventTypeId"]
            completion_event_type_id = self.jbody["completionEventTypeId"]
            intermediate = self.jbody["intermediate"]
            description = self.jbody["description"]
        except KeyError as err:
            raise exc.BadRequest("Missing Required Argument: {}".format(err.message))
        except ValueError as err:
            raise exc.BadRequest(err.message)

        creation_event_type = (
            self.session.query(EventType).get(creation_event_type_id)
        )

        if creation_event_type is None:
            self.write_error(400, message="Bad creation event type")
            return

        completion_event_type = (
            self.session.query(EventType).get(completion_event_type_id)
        )

        if completion_event_type is None:
            self.write_error(400, message="Bad event type")
            return

        try:
            fate = Fate.create(
                self.session, creation_event_type, completion_event_type,
                intermediate=intermediate, description=description
            )
        except IntegrityError as err:
            raise exc.Conflict(err.orig.message)
        except exc.ValidationError as err:
            raise exc.BadRequest(err.message)

        self.session.commit()

        json = fate.to_dict("/api/v1")
        json["href"] = "/api/v1/fates/{}".format(fate.id)

        self.created("/api/v1/fates/{}".format(fate.id), json)

    def get(self):
        """ Get all Fates

        Example Request:

            GET /api/v1/fates HTTP/1.1
            Host: localhost

        Example response:

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                limit: int,
                page: int,
                totalFates: int,
                fates: [
                    {
                        id: int,
                        creationEventTypeId: int,
                        completionEventType: int,
                        intermediate: true|false,
                        description: string,
                    },
                    ...
                ],
            }
        """
        fates = self.session.query(Fate)

        offset, limit, expand = self.get_pagination_values()
        hosts, total = self.paginate_query(fates, offset, limit)

        json = {
            "limit": limit,
            "offset": offset,
            "totalFates": total,
            "fates": [fate.to_dict("/api/v1") for fate in fates.all()],
        }

        self.success(json)


class FateHandler(ApiHandler):
    def get(self, id):
        """Get a specific Fate

        Example Request:

            GET /api/v1/fates/1/ HTTP/1.1
            Host: localhost

        Example response:

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "status": "ok",
                id: 1,
                creationEventTypeId: 1,
                completionEventTypeId: 2,
                intermediate: false,
                description: "This is a fate"
            }

        Args:
            id: the id of the fate to get
        """
        offset, limit, expand = self.get_pagination_values()
        fate = self.session.query(Fate).filter_by(id=id).scalar()
        if not fate:
            raise exc.NotFound("No such Fate {} found".format(id))

        json = fate.to_dict("/api/v1")

        if "eventtypes" in expand:
            json["creationEventType"] = (
                fate.creation_event_type.to_dict("/api/v1")
            )
            json["competionEventType"] = (
                fate.completion_event_type.to_dict("/api/v1")
            )

        self.success(json)

    def put(self, id):
        """Update a Fate

        Example Request:

            PUT /api/v1/fates/1 HTTP/1.1
            Host: localhost
            Content-Type: application/json
            X-NSoT-Email: user@localhost

            {
                "description": "New desc",
                "intermediate: true
            }

        Example response:

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "status": "ok",
                id: 1,
                creationEventTypeId: 1,
                completionEventTypeId: 2,
                intermediate: true,
                description: "New desc"
            }

        Args:
            id: the id of the fate to update
        """
        fate = self.session.query(Fate).filter_by(id=id).scalar()
        if not fate:
            raise exc.NotFound("No such Fate {} found".format(id))

        new_desc = None
        new_intermediate = None
        try:
            if "description" in self.jbody:
                new_desc = self.jbody["description"]
            if "intermediate" in self.jbody:
                new_intermediate = self.jbody['intermediate']
        except KeyError as err:
            raise exc.BadRequest("Missing Required Argument: {}".format(err.message))

        try:
            if new_desc:
                fate = fate.update(
                    description=new_desc
                )
            if new_intermediate is not None:
                fate = fate.update(
                    intermediate=new_intermediate
                )

        except IntegrityError as err:
            raise exc.Conflict(str(err.orig))

        json = fate.to_dict("/api/v1")

        self.success(json)

    def delete(self, id):
        """Delete a Fate

        Not supported
        """
        self.not_supported()


class LaborsHandler(ApiHandler):

    def post(self):
        """ Create a Labor entry

        Not supported.  Labors are only created by Fates.
        """
        self.not_supported()

    def get(self):
        """ Get all Labors

        Example Request:

            GET /api/v1/labors HTTP/1.1
            Host: localhost

        Example response:

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "status": "ok",
                "limit": int,
                "offset": int,
                "totalFates": int,
                "labors": [
                    {
                        "id": 23,
                        "questId": 5,
                        "hostId": 26,
                        "creationTime": timestamp,
                        "ackTime": timestamp,
                        "ackUser": string,
                        "completionTime": timestamp,
                        "creationEventId": 127,
                        "completionEventId": 212,
                    },
                    ...
                ],
            }
        """
        hostname = self.get_argument("hostname", None)

        labors = self.session.query(Labor)
        if hostname is not None:
            labors = (
                labors.filter_by(hostname=hostname)
                .order_by(desc(Labor.creation_time))
            )

        offset, limit, expand = self.get_pagination_values()
        labors, total = self.paginate_query(labors, offset, limit)

        labors = labors.from_self().order_by(Labor.creation_time)

        json = {
            "limit": limit,
            "offset": offset,
            "totalLabors": total,
            "labors": [labor.to_dict("/api/v1") for labor in labors.all()],
        }

        self.success(json)


class LaborHandler(ApiHandler):
    def get(self, id):
        """Get a specific Labor

        Example Request:

            GET /api/v1/labors/1 HTTP/1.1
            Host: localhost

        Example response:

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "status": "ok",
                "id": 23,
                "questId": 5,
                "hostId": 26,
                "creationTime": timestamp,
                "ackTime": timestamp,
                "ackUser": string,
                "completionTime": timestamp,
                "creationEventId": 127,
                "completionEventId": 212,
            }

        Args:
            hostname: the name of the host to get
        """
        offset, limit, expand = self.get_pagination_values()
        labor = self.session.query(Labor).filter_by(id=id).scalar()
        if not labor:
            raise exc.NotFound("No such Labor {} found".format(id))

        json = labor.to_dict("/api/v1")

        if "hosts" in expand:
            json["host"] = labor.host.to_dict("/api/v1")

        if "eventtypes" in expand:
            json["creationEvent"] = labor.creation_event.to_dict("/api/v1")
            if labor.completion_event:
                json["competionEvent"] = (
                    labor.completion_event.to_dict("/api/v1")
                )

        self.success(json)

    def put(self, id):
        """Update a Labor

        Example Request:

            PUT /api/v1/labors/23 HTTP/1.1
            Host: localhost
            Content-Type: application/json
            X-NSoT-Email: user@localhost

            {
                "questId": 1,
            }

            or

            {
                "ackUser": "johnny"
            }

        Example response:

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "status": "ok",
                "id": 23,
                "questId": 1,
                "hostId": 26,
                "creationTime": timestamp,
                "ackTime": timestamp,
                "ackUser": "johnny",
                "completionTime": timestamp,
                "creationEventId": 127,
                "completionEventId": 212,
            }

        Args:
            id: the id of the Labor to update
        """
        labor = self.session.query(Labor).filter_by(id=id).scalar()
        if not labor:
            raise exc.NotFound("No such Labor {} found".format(id))

        quest_id = None
        ack_user = None
        try:
            if "questId" in self.jbody:
                quest_id = self.jbody["questId"]

            if "ackUser" in self.jbody:
                ack_user = self.jbody["ackUser"]

            if not quest_id and not ack_user:
                raise exc.BadRequest("Must update either questId or ackUser")
        except KeyError as err:
            raise exc.BadRequest("Missing Required Argument: {}".format(err.message))

        try:
            if quest_id:
                labor.update(quest_id=quest_id)
            if ack_user:
                labor.acknowledge(ack_user)
        except IntegrityError as err:
            raise exc.Conflict(str(err.orig))

        json = labor.to_dict("/api/v1")

        self.success(json)

    def delete(self, id):
        """Delete a Labor

        Not supported
        """
        self.not_supported()


class QuestsHandler(ApiHandler):
    def post(self):
        """ Create a Quest entry

        Example Request:

            POST /api/v1/quests HTTP/1.1
            Host: localhost
            Content-Type: application/json
            {
                "eventTypeId": 1,
                "creator": "johnny",
                "targetTime": timestamp,
                "description": "This is a quest almighty",
                "hostnames": [],
                "hostQuery": "tag=value"
            }

        Example response:

            HTTP/1.1 201 OK
            Location: /api/v1/hosts/example

            {
                "status": "created",
                "id": 1,
                "creator": "johnny",
                "embarkTime": timestamp,
                "targetTime": timestamp,
                "completionTime": timestamp,
                "description": "This is a quest almighty",
                "labors": [],
            }

        """
        try:
            event_type_id = self.jbody["eventTypeId"]
            creator = self.jbody["creator"]
            description = self.jbody["description"]
            hostnames = self.jbody["hostnames"]

            if "targetTime" in self.jbody:
                target_time = parser.parse(
                    self.jbody["targetTime"]
                )
            else:
                target_time = None
        except KeyError as err:
            raise exc.BadRequest("Missing Required Argument: {}".format(err.message))
        except ValueError as err:
            raise exc.BadRequest(err.message)

        event_type = (
            self.session.query(EventType).get(event_type_id)
        )

        if event_type is None:
            self.write_error(400, message="Bad creation event type")
            return

        if "hostQuery" in self.jbody:
            query = self.jbody["hostQuery"]
            response = PluginHelper.request_get(params={"query": query})
            if response.json()["status"] == "ok":
                for hostname in response.json()["results"]:
                    hostnames.append(hostname)

        hosts = []
        for hostname in hostnames:
            if not hostname:
                continue
            host = Host.get_host(self.session, hostname)
            if host is None:
                Host.create(self.session, hostname)
            hosts.append(hostname)

        if len(hosts) == 0:
            raise exc.BadRequest("No hosts found with given list")

        try:
            quest = Quest.create(
                self.session, creator, hosts, event_type, target_time,
                description=description
            )
        except IntegrityError as err:
            raise exc.Conflict(err.orig.message)
        except exc.ValidationError as err:
            raise exc.BadRequest(err.message)

        self.session.commit()

        json = quest.to_dict("/api/v1")

        json["labors"] = (
            [labor.to_dict("/api/v1")
             for labor in quest.get_open_labors()]
        )

        self.created("/api/v1/quests/{}".format(quest.id), json)

    def get(self):
        """ Get all Quests

        Example Request:

            GET /api/v1/quests HTTP/1.1
            Host: localhost

        Example response:

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "status": "ok",
                "limit": int,
                "offset": int,
                "totalQuests": int,
                "quests": [
                    {
                        "id": 1,
                        "creator": "johnny",
                        "embarkTime": timestamp,
                        "completionTime": timestamp,
                        "labors": [],
                        "description": "Some description"
                    },
                    ...
                ],
            }
        """
        filter_closed = self.get_argument("filterClosed", None)

        quests = self.session.query(Quest).order_by(desc(Quest.embark_time))

        if filter_closed:
            quests = quests.filter(Quest.completion_time == None)

        offset, limit, expand = self.get_pagination_values()
        quests, total = self.paginate_query(quests, offset, limit)

        quests = quests.from_self().order_by(Quest.embark_time)

        quests_json = []
        for quest in quests.all():
            quest_json = quest.to_dict("/api/v1")
            if "labors" in expand:
                quest_json["labors"] = [
                    labor.to_dict("/api/v1")
                    for labor in quest.labors
                ]
            quests_json.append(quest_json)

        json = {
            "limit": limit,
            "offset": offset,
            "totalQuests": total,
        }

        json["quests"] = quests_json

        self.success(json)


class QuestHandler(ApiHandler):
    def get(self, id):
        """Get a specific Quest

        Example Request:

            GET /api/v1/quests/1 HTTP/1.1
            Host: localhost

        Example response:

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "status": "ok",
                "id": 1,
                "creator": "johnny",
                "embarkTime": timestamp,
                "completionTime": timestamp,
                "description": "This is a quest almighty",
                "labors": [],
            }

        Args:
            id: the id of the quest to get
        """
        offset, limit, expand = self.get_pagination_values()

        quest = self.session.query(Quest).filter_by(id=id).scalar()

        if not quest:
            raise exc.NotFound("No such Quest {} found".format(id))

        json = quest.to_dict("/api/v1")

        if "labors" in expand:
            json["labors"] = []
            for labor in quest.labors:
                labor_json = labor.to_dict("/api/v1")
                if "hosts" in expand:
                    labor_json["host"] = labor.host.to_dict("/api/v1")
                if "events" in expand:
                    labor_json["creationEvent"] = (
                        labor.creation_event.to_dict("/api/v1")
                    )
                    if "eventtypes" in expand:
                        labor_json["creationEvent"]["eventType"] = (
                            labor.creation_event.event_type.to_dict("/api/v1")
                        )
                        if labor.completion_event:
                            labor_json["completionEvent"] = (
                                labor.completion_event.to_dict("/api/v1")
                            )
                            labor_json["completionEvent"]["eventType"] = (
                                labor.completion_event
                                .event_type.to_dict("/api/v1")
                            )
                        else:
                            labor_json["completionEvent"] = None
                json["labors"].append(labor_json)
        else:
            json["labors"] = []
            for labor in quest.labors:
                json["labors"].append({
                    "id": labor.id,
                    "href": labor.href("/api/v1")
                })

        self.success(json)

    def put(self, id):
        """Update a Quest

         Example Request:

             PUT /api/v1/quest/1 HTTP/1.1
             Host: localhost
             Content-Type: application/json
             X-NSoT-Email: user@localhost

             {
                 "description": "New desc",
                 "creator": "tammy"
             }

         Example response:

             HTTP/1.1 200 OK
             Content-Type: application/json

             {
                 "status": "ok",
                 "id": 1,
                 "creator": "johnny",
                 "embarkTime": timestamp,
                 "completionTime": timestamp,
                 "description": "New desc",
                 "labors": [],
             }

         Args:
             id: the id of the fate to update
         """
        quest = self.session.query(Quest).filter_by(id=id).scalar()

        if not quest:
            raise exc.NotFound("No such Quest {} found".format(id))

        new_desc = None
        new_creator = None
        try:
            if "description" in self.jbody:
                new_desc = self.jbody["description"]
            if "creator" in self.jbody:
                new_creator = self.jbody['creator']
        except KeyError as err:
            raise exc.BadRequest(
                "Missing Required Argument: {}".format(err.message))

        try:
            if new_desc:
                quest = quest.update(
                    description=new_desc
                )
            if new_creator is not None:
                quest = quest.update(
                    creator=new_creator
                )

        except IntegrityError as err:
            raise exc.Conflict(str(err.orig))

        json = quest.to_dict("/api/v1")

        self.success(json)

    def delete(self, id):
        """Delete a Quest

        Not supported
        """
        self.not_supported()