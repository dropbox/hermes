import ipaddress
import logging
from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError


from .util import ApiHandler
from .. import exc
from ..models import Host, EventType, Event, Labor, Fate
from ..util import qp_to_bool as qpbool, parse_set_query


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

        Example response:

            HTTP/1.1 201 OK
            Location: /api/v1/hosts/example

            {
                "status": "create",
                "id": 1,
                "hostname": "example"
            }
        """

        try:
            hostname = self.jbody["hostname"]
        except KeyError as err:
            raise exc.BadRequest("Missing Required Argument: {}".format(err.message))
        except ValueError as err:
            raise exc.BadRequest(err.message)

        try:
            host = Host.create(
                self.session, hostname
            )
        except IntegrityError as err:
            raise exc.Conflict(err.orig.message)
        except exc.ValidationError as err:
            raise exc.BadRequest(err.message)

        self.session.commit()

        json = host.to_dict("/api/v1")
        json['href'] = "/api/v1/hosts/{}".format(host.hostname)
        json['status'] = 'created'

        self.created("/api/v1/hosts/{}".format(host.hostname), json)

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
                "data": {
                    "hosts": [
                        {
                            "id": 1
                            "name": "Site 1",
                            "description": ""
                        }
                    ],
                    "limit": null,
                    "offset": 0,
                    "total": 1,
                }
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
                "data": {
                    "host": {
                        "id": 1,
                        "hostname": "example",
                    }
                }
            }

        Args:
            hostname: the name of the host to get
        """
        offset, limit, expand = self.get_pagination_values()
        host = self.session.query(Host).filter_by(hostname=hostname).scalar()
        if not host:
            raise exc.NotFound("No such Host {} found".format(hostname))

        json = host.to_dict("/api/v1")
        json['limit'] = limit
        json['offset'] = offset


        # add the labors and quests
        labors = []
        quests = []
        for labor in (
                host.get_labors().limit(limit).offset(offset)
                .from_self().order_by(Labor.creation_time).all()
        ):
            if "labors" in expand:
                labors.append(labor.to_dict("/api/v1"))
            else:
                labors.append({"id": labor.id, "href": labor.href("/api/v1")})

            if "quests" in expand:
                quests.append(labor.quest.to_dict("/api/v1"))
            else:
                quests.append(
                    {
                        "id": labor.quest.id,
                        "href": labor.quest.href("/api/v1")
                    }
                )
        json['labors'] = labors
        json['quests'] = quests

        # add the events
        events = []
        events_query = host.get_latest_events()
        last_event = host.get_latest_events().first()
        for event in (
                host.get_latest_events().limit(limit).offset(offset)
                .from_self().order_by(Event.timestamp).all()
        ):
            if "events" in expand:
                events.append(event.to_dict("/api/v1"))
            else:
                events.append({
                    "id": event.id, "href": event.href("/api/v1")
                })
        json['lastEvent'] = str(last_event.timestamp)
        json['events'] = events

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
                "data": {
                    "site": {
                        "id": 1,
                        "hostname": "newname",
                    }
                }
            }

        Args:
            hostname: the hostname to update
        """
        host = self.session.query(Host).filter_by(hostname=hostname).scalar()
        if not host:
            raise exc.NotFound("No such Host {} found".format(hostname))

        try:
            hostname = self.jbody["hostname"]
        except KeyError as err:
            raise exc.BadRequest("Missing Required Argument: {}".format(err.message))

        try:
            host.update(
                hostname=hostname,
            )
        except IntegrityError as err:
            raise exc.Conflict(str(err.orig))

        self.success({
            "host": host.to_dict("/api/v1"),
        })

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

        Example response:

            HTTP/1.1 201 OK
            Location: /api/v1/eventtypes/1

            {
                "status": "ok",
                "data": {
                    "eventType": {
                        "id": 1,
                        "category": "system-reboot",
                        "state": "required",
                        "description": "System requires a reboot.",
                    }
                }
            }
        """

        try:
            category = self.jbody['category']
            state = self.jbody['state']
            description = self.jbody['description']
        except KeyError as err:
            raise exc.BadRequest("Missing Required Argument: {}".format(err.message))
        except ValueError as err:
            raise exc.BadRequest(err.message)

        try:
            event_type = EventType.create(
                self.session, category, state, description=description
            )
        except IntegrityError as err:
            raise exc.Conflict(err.orig.message)
        except exc.ValidationError as err:
            raise exc.BadRequest(err.message)

        self.session.commit()

        json = event_type.to_dict("/api/v1")
        json['href'] = "/api/v1/eventtypes/{}".format(event_type.id)
        json['status'] = 'created'

        self.created("/api/v1/eventtypes/{}".format(event_type.id), json)

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
                "data": {
                    "eventTypes": [
                        {
                            "eventType": {
                            "id": 1,
                            "category": "system-reboot",
                            "state": "required",
                            "description": "System requires a reboot.",
                        }
                    ],
                    "limit": 10,
                    "offset": 0,
                    "totalEventTypes": 1,
                }
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
                id: 1,
                category: "system-reboot",
                state: "required",
                description: "This system requires a reboot",
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
        json['limit'] = limit
        json['offset'] = offset

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
        json['events'] = events

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
        json['fate'] = fates

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
                "data": {
                    "eventType": {
                        "id": 1,
                        category: "system-reboot",
                        state: "required",
                        description: "New description",
                    }
                }
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

        self.success({
            "eventType": event_type.to_dict("/api/v1"),
        })

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
            hostname = self.jbody['hostname']
            user = self.jbody['user']
            event_type_id = self.jbody['eventTypeId']
            note = self.jbody['note']
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

        json = host.to_dict("/api/v1")
        json['href'] = "/api/v1/events/{}".format(event.id)
        json['status'] = 'created'

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
            json['host'] = event.host.to_dict("/api/v1")

        if "eventtypes" in expand:
            json['eventType'] = event.event_type.to_dict("/api/v1")

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
            creation_event_type_id = self.jbody['creationEventTypeId']
            completion_event_type_id = self.jbody['completionEventTypeId']
            intermediate = self.jbody['intermediate']
            description = self.jbody['description']
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
        json['href'] = "/api/v1/fates/{}".format(fate.id)

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
        json['limit'] = limit
        json['offset'] = offset

        if "eventtypes" in expand:
            json['creationEventType'] = (
                fate.creation_event_type.to_dict('/api/v1')
            )
            json['competionEventType'] = (
                fate.completion_event_type.to_dict('/api/v1')
            )

        self.success(json)

    def put(self, id):
        """Update a Fate

        Not supported
        """
        self.not_supported()

    def delete(self, id):
        """Delete a Fate

        Not supported
        """
        self.not_supported()