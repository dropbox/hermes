from __future__ import division


from datetime import datetime
from dateutil import parser, tz
import json
import logging
import pytz
import random
import re
import sqlalchemy
from sqlalchemy import desc, or_, and_
from sqlalchemy.exc import IntegrityError
import string
import time


from .util import ApiHandler
from ..util import id_generator, PluginHelper, email_message
from .. import exc
from ..models import Host, EventType, Event, Labor, Fate, Quest
from ..settings import settings


log = logging.getLogger(__name__)

EMAIL_REGEX = re.compile(r"[^@]+@[^@]+\.[^@]+")


class HostsHandler(ApiHandler):

    def post(self):
        """**Create a Host entry**

        **Example Request:**

        .. sourcecode:: http

            POST /api/v1/hosts HTTP/1.1
            Host: localhost
            Content-Type: application/json
            {
                "hostname": "example"
            }

        or:

        .. sourcecode:: http

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

        **Example response:**

        .. sourcecode:: http

            HTTP/1.1 201 OK
            Location: /api/v1/hosts/example

            {
                "status": "created",
                "href": "/api/v1/hosts/example",
                "id": 1,
                "hostname": "example"
            }

        or:

        .. sourcecode: http

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

        :reqjson string hostname: The hostname of the server

        :reqheader Content-Type: The server expects a json body specified with
                                 this header.

        :resheader Location: URL to the created resource.

        :statuscode 201: The Host was successfully created.
        :statuscode 400: The request was malformed.
        :statuscode 401: The request was made without being logged in.
        :statuscode 409: There was a conflict with another resource.
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

        log.info("HOSTS: Create {}".format(", ".join(
            [
                host["hostname"] for host in hostnames
            ]
        )))

        try:
            hosts = []
            for hostname in hostnames:
                host = Host.create(self.session, hostname["hostname"])
                hosts.append(host.to_dict(self.href_prefix))
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

        log.info("HOST: Created {}".format(", ".join(
            [host["hostname"] for host in hostnames]
        )))

    def get(self):
        """**Get all Hosts**

        **Example Request:**

        .. sourcecode:: http

            GET /api/v1/hosts HTTP/1.1
            Host: localhost

        **Example response:**

        .. sourcecode:: http

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

        :query string hostname: (*optional*) Filter Hosts by hostname.
        :query string hostQuery: (*optional*) the query to send to the plugin to come up with the list of hostnames
        :query int limit: (*optional*) Limit result to N resources.
        :query int offset: (*optional*) Skip the first N resources.

        :statuscode 200: The request was successful.
        :statuscode 401: The request was made without being logged in.
        """
        hostname = self.get_argument("hostname", None)
        host_query = self.get_argument("hostQuery", None)

        hosts = self.session.query(Host)
        if hostname is not None:
            hosts = hosts.filter_by(hostname=hostname)

        hostnames = []
        if host_query:
            response = PluginHelper.request_get(params={"query": host_query})
            if (
                response.status_code == 200
                and response.json()["status"] == "ok"
            ):
                for hostname in response.json()["results"]:
                    hostnames.append(hostname)
            else:
                raise exc.BadRequest("Bad host query: {}".format(host_query))

        if hostnames:
            hosts = hosts.filter(Host.hostname.in_(hostnames))

        offset, limit, expand = self.get_pagination_values()
        hosts, total = self.paginate_query(hosts, offset, limit)

        json = {
            "limit": limit,
            "offset": offset,
            "totalHosts": total,
            "hosts": [
                host.to_dict(
                    base_uri=self.href_prefix, expand=set(expand)
                ) for host in hosts.all()
            ],
        }

        self.success(json)


class HostHandler(ApiHandler):
    def get(self, hostname):
        """**Get a specific Host**

        **Example Request:**

        .. sourcecode:: http

            GET /api/v1/hosts/example HTTP/1.1
            Host: localhost

        **Example response:**

        .. sourcecode:: http

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

        :param hostname: hostname of the Host to retrieve
        :type hostname: string

        :query string expand: (*optional*) supports labors, events, eventtypes, quests
        :query int limit: (*optional*) Limit result of child resources.
        :query int offset: (*optional*) Skip the first N child resources.

        :statuscode 200: The request was successful.
        :statuscode 401: The request was made without being logged in.
        :statuscode 404: The Host was not found.
        """
        offset, limit, expand = self.get_pagination_values()
        host = self.session.query(Host).filter_by(hostname=hostname).scalar()
        if not host:
            raise exc.NotFound("No such Host {} found".format(hostname))

        json = host.to_dict(self.href_prefix)
        json["limit"] = limit
        json["offset"] = offset

        # add the labors and quests
        labors = []
        quests = []

        # We will perform labor and quest expansion here b/c we want to apply
        # limits and offsets
        for labor in (
                host.get_labors().limit(limit).offset(offset)
                .from_self().order_by(Labor.creation_time).all()
        ):
            if "labors" in expand:
                labors.append(
                    labor.to_dict(
                        base_uri=self.href_prefix, expand=set(expand)
                    )
                )
            else:
                labors.append({
                    "id": labor.id, "href": labor.href(self.href_prefix)
                })

            if labor.quest and "quests" in expand:
                quests.append(
                    labor.quest.to_dict(self.href_prefix, expand=set(expand))
                )
            elif labor.quest:
                quests.append(
                    {
                        "id": labor.quest.id,
                        "href": labor.quest.href(self.href_prefix)
                    }
                )
        json["labors"] = labors
        json["quests"] = quests

        # We will perform the events expansion here b/c we want to apply
        # limits and offsets
        events = []
        last_event = host.get_latest_events().first()
        for event in (
                host.get_latest_events().limit(limit).offset(offset)
                .from_self().order_by(Event.timestamp).all()
        ):
            if "events" in expand:
                events.append(
                    event.to_dict(
                        base_uri=self.href_prefix, expand=set(expand)
                    )
                )
            else:
                events.append({
                    "id": event.id, "href": event.href(self.href_prefix)
                })

        if last_event:
            json["lastEvent"] = str(last_event.timestamp)
        else:
            json["lastEvent"] = None
        json["events"] = events

        self.success(json)

    def put(self, hostname):
        """**Update a Host**

        **Example Request:**

        .. sourcecode:: http

            PUT /api/v1/hosts/example HTTP/1.1
            Host: localhost
            Content-Type: application/json

            {
                "hostname": "newname",
            }

        **Example response:**

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "status": "ok",
                "id": 1,
                "href": "/api/v1/hosts/example",
                "hostname": "newname",
            }

        :param hostname: hostname of the Host that should be updated.
        :type hostname: string

        :reqjson string hostname: The new hostname of the Host.

        :reqheader Content-Type: The server expects a json body specified with
                                 this header.

        :statuscode 200: The request was successful.
        :statuscode 400: The request was malformed.
        :statuscode 401: The request was made without being logged in.
        :statuscode 403: The request was made with insufficient permissions.
        :statuscode 404: The Host at hostname was not found.
        :statuscode 409: There was a conflict with another resource.
        """
        log.info("HOS: Update {}".format(hostname))

        host = self.session.query(Host).filter_by(hostname=hostname).scalar()
        if not host:
            raise exc.NotFound("No such Host {} found".format(hostname))

        try:
            new_hostname = self.jbody["hostname"]
        except KeyError as err:
            raise exc.BadRequest(
                "Missing Required Argument: {}".format(err.message)
            )

        host = host.update_name(new_hostname);

        json = host.to_dict(self.href_prefix)

        self.success(json)

        log.info("HOST: Renamed {} to {}".format(hostname, new_hostname))

    def delete(self, hostname):
        """**Delete a Host**

        *Not supported*
        """
        self.not_supported()


class EventTypesHandler(ApiHandler):

    def post(self):
        """**Create a EventType entry**

        **Example Request:**

        .. sourcecode:: http

            POST /api/v1/eventtypes HTTP/1.1
            Host: localhost
            Content-Type: application/json
            {
                "category": "system-reboot",
                "state": "required",
                "description": "System requires a reboot.",
            }

        or:

        .. sourcecode:: http

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
                        "description": "Some description",
                         "restricted": true,
                    },
                    {
                        "category": "tango",
                        "state": "foxtrot",
                        "description": "Some description"
                    }
                ]
            }

        **Example response:**

        .. sourcecode:: http

            HTTP/1.1 201 OK
            Location: /api/v1/eventtypes/1

            {
                "status": "created",
                "id": 1,
                "category": "system-reboot",
                "state": "required",
                "description": "System requires a reboot.",
                "restricted": false,
            }

        or:

        .. sourcecode:: http

            {
                "status": "created",
                "eventTypes":
                [
                    {
                        "category": "foo",
                        "state": "bar",
                        "href": "/api/v1/eventtypes/7",
                        "id": 7,
                        "description": "Some description",
                        "restricted": false,
                    },
                    {
                        "category": "foo",
                        "state": "baz",
                        "href": "/api/v1/eventtypes/8",
                        "id": 8,
                        "description": "Some description",
                        "restricted": true,
                    },
                    {
                        "category": "tango",
                        "state": "foxtrot",
                        "href": "/api/v1/eventtypes/9",
                        "id": 9,
                        "description": "Some description",
                        "restricted": false,
                    }
                ],
                "totalEventTypes": 3
            }

        :reqjson string category: The category value of the EventType
        :regjson string state: The state value of the EventType
        :regjson string description: The human readable description of the EventType
        :regjson boolean restricted: (*optional*) If true, the EventType
                                    created will be restricted such that
                                    only direct API calls can throw events of
                                    that type (and the CLI/WebGUI would refuse)

        :reqheader Content-Type: The server expects a json body specified with
                                 this header.

        :resheader Location: URL to the created resource.

        :statuscode 201: The site was successfully created.
        :statuscode 400: The request was malformed.
        :statuscode 401: The request was made without being logged in.
        :statuscode 409: There was a conflict with another resource.
        """

        try:
            if "eventTypes" in self.jbody:
                event_types = self.jbody["eventTypes"]
            else:
                event_types = [
                    {
                        "category": self.jbody["category"],
                        "state": self.jbody["state"],
                        "description": self.jbody["description"],
                        "restricted": self.jbody.get("restricted", False)
                    }
                ]

        except KeyError as err:
            raise exc.BadRequest(
                "Missing Required Argument: {}".format(err.message)
            )
        except ValueError as err:
            raise exc.BadRequest(err.message)

        log.info("EVENTTYPE: Creating {}".format(", ".join(
            [
                "{} {}".format(event_type['category'], event_type['state'])
                for event_type in event_types
            ]
        )))

        try:
            created_types = []
            for x in range(0, len(event_types)):
                created_type = EventType.create(
                    self.session, event_types[x]["category"],
                    event_types[x]["state"],
                    description=event_types[x]["description"],
                    restricted=event_types[x].get("restricted", False)
                )
                created_types.append(created_type.to_dict(self.href_prefix))
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

        log.info("EVENTTYPE: Created {}".format(", ".join(
            [
                "{} {}".format(event_type['category'], event_type['state']) for event_type in event_types
            ]
        )))

    def get(self):
        """**Get all EventTypes**

        **Example Request:**

        .. sourcecode:: http

            GET /api/v1/eventtypes HTTP/1.1
            Host: localhost

        **Example response:**

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "status": "ok",
                "limit": 10,
                "offset": 0,
                "totalEventTypes": 3,
                "eventTypes": [
                    {
                        "id": 1,
                        "category": "foo",
                        "state": "bar",
                        "description": "Foo bar all the way",
                        "href": "/api/v1/eventtypes/1"
                    },
                    ...
                ],
            }

        :query string category: (*optional*) Filter EventTypes by category.
        :query string state: (*optional*) Filter EventTypes by state.
        :query int limit: (*optional*) Limit result to N resources.
        :query int offset: (*optional*) Skip the first N resources.
        :query boolean startingTypes: (*optional*) Return the event types that can create non-intermediate Labors

        :statuscode 200: The request was successful.
        :statuscode 401: The request was made without being logged in.
        """
        category = self.get_argument("category", None)
        state = self.get_argument("state", None)
        starting_types = self.get_argument("startingTypes", False);

        event_types = self.session.query(EventType)
        if category is not None:
            event_types = event_types.filter_by(category=category)

        if state is not None:
            event_types = event_types.filter_by(state=state)

        if starting_types:
            starting_event_types = (
                self.session.query(Fate)
                    .filter(Fate.follows_id == None)
                    .group_by(Fate.creation_type_id).all()
            )
            event_types = (
                event_types.filter(EventType.id.in_(
                    e_type.creation_type_id for e_type in starting_event_types
                ))
            )

        offset, limit, expand = self.get_pagination_values()
        event_types, total = self.paginate_query(event_types, offset, limit)

        json = {
            "limit": limit,
            "offset": offset,
            "totalEventTypes": total,
            "eventTypes": (
                [
                    event_type.to_dict(
                        base_uri=self.href_prefix, expand=set(expand)
                    )
                    for event_type in event_types.all()
                ]
            ),
        }

        self.success(json)


class EventTypeHandler(ApiHandler):
    def get(self, id):
        """**Get a specific EventType**

        **Example Request:**

        .. sourcecode:: http

            GET /api/v1/eventtypes/1/ HTTP/1.1
            Host: localhost

        **Example response:**

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "status": "ok",
                "id": 1,
                "category": "system-reboot",
                "state": "required",
                "description": "This system requires a reboot",
                "events": [],
                "autoCreates": [],
                "autoCompletes": []
                "limit": 10,
                "offset": 0
            }

        :param id: id of the EventType to retrieve
        :type id: int

        :query string expand: (*optional*) supports events, fates
        :query int limit: (*optional*) Limit result of child resources.
        :query int offset: (*optional*) Skip the first N child resources.

        :statuscode 200: The request was successful.
        :statuscode 401: The request was made without being logged in.
        :statuscode 404: The EventType was not found.
        """
        offset, limit, expand = self.get_pagination_values()
        event_type = (
            self.session.query(EventType).filter_by(id=id).scalar()
        )
        if not event_type:
            raise exc.NotFound("No such EventType {} found".format(id))

        json = event_type.to_dict(self.href_prefix)
        json["limit"] = limit
        json["offset"] = offset

        # We will perform expansion of events here b/c we want to apply
        # limits and offsets
        events = []
        for event in (
                event_type.get_latest_events().limit(limit).offset(offset)
                .from_self().order_by(Event.timestamp).all()
        ):
            if "events" in expand:
                events.append(
                    event.to_dict(
                        base_uri=self.href_prefix, expand=set(expand)
                    )
                )
            else:
                events.append({
                    "id": event.id, "href": event.href(self.href_prefix)
                })
        json["events"] = events

        self.success(json)

    def put(self, id):
        """**Update an EventType**

        **Example Request:**

        .. sourcecode:: http

            PUT /api/v1/eventtypes/1/ HTTP/1.1
            Host: localhost
            Content-Type: application/json

            {
                "description": "New description",
            }

        **Example response:**

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "status": "ok",
                "id": 1,
                "href": "/api/v1/eventtypes/1",
                "category": "system-reboot",
                "state": "required",
                "description": "New description",
            }

        :param id: id of the EventType that should be updated.
        :type id: string

        :reqjson string description: The new description of the EventType.

        :reqheader Content-Type: The server expects a json body specified with
                                 this header.

        :statuscode 200: The request was successful.
        :statuscode 400: The request was malformed.
        :statuscode 401: The request was made without being logged in.
        :statuscode 403: The request was made with insufficient permissions.
        :statuscode 404: The EventType was not found.
        :statuscode 409: There was a conflict with another resource.
        """

        log.info("EVENTTYPE: Updating {}".format(id))

        event_type = (
            self.session.query(EventType).filter_by(id=id).scalar()
        )
        if not event_type:
            raise exc.NotFound("No such EventType {} found".format(id))

        try:
            description = self.jbody["description"]
        except KeyError as err:
            raise exc.BadRequest(
                "Missing Required Argument: {}".format(err.message)
            )

        try:
            event_type.update(
                description=description,
            )
        except IntegrityError as err:
            raise exc.Conflict(str(err.orig))

        json = event_type.to_dict(self.href_prefix)

        self.success(json)

        log.info("EVENTTYPE: Updated {} with desc {}".format(id, description))

    def delete(self, id):
        """**Delete an EventType**

        *Not supported*
        """
        self.not_supported()


class EventsHandler(ApiHandler):
    def post(self):
        """**Create an Event entry**

        **Example Request:**

        .. sourcecode:: http

            POST /api/v1/events HTTP/1.1
            Host: localhost
            Content-Type: application/json
            {
                "hostname": "example",
                "user": "johnny",
                "eventTypeId": 3,
                "note": "Sample description"
            }

        or

        .. sourcecode:: http

            POST /api/v1/events HTTP/1.1
            Host: localhost
            Content-Type: application/json
            {
                "hostname": "example",
                "user": "johnny",
                "category": "system-reboot",
                "state": "completed",
                "note": "Sample description"
            }

        or

        .. sourcecode:: http

            POST /api/v1/events HTTP/1.1
            Host: localhost
            Content-Type: application/json
            {
                "hostQuery": "tag=value",
                "user": "johnny",
                "eventTypeId": 3,
                "note": "Sample description"
            }

        or

        .. sourcecode:: http

            POST /api/v1/events HTTP/1.1
            Host: localhost
            Content-Type: application/json
            {
                "questId": 1,
                "user": "johnny",
                "eventTypeId": 3,
                "note": "Sample description"
            }

        **Example response:**

        .. sourcecode:: http

            HTTP/1.1 201 OK
            Location: /api/v1/events/1

            {
                "status": "created",
                "id": 1,
                "href": "/api/v1/events/1",
                "hostname": "example",
                "user": "johnny",
                "eventTypeId": 3,
                "note": "Sample description"
            }

        or

        .. sourcecode:: http

        HTTP/1.1 201 OK
            Location: /api/v1/events/1

            {
                "status": "created",
                "events": [{
                    "id": 1,
                    "href": "/api/v1/events/1",
                    "hostname": "example",
                    "user": "johnny",
                    "eventTypeId": 3,
                    "note": "Sample description"
                },
                ...
                ]
            }

        :reqjson string hostname: (*optional*) The hostname of the Host of this Event
        :regjson string hostnames: (*optional*) The list of hostnames for which we want to throw this Event
        :reqjson string hostQuery: (*optional*) The external query to run to get Hosts for which to create Events
        :regjson int questId: (*optional*) The Quest ID which has hosts for which we want to create Events
        :regjson string user: The user responsible for throwing this Event
        :regjson int eventTypeId: The id of the EventType
        :regjson string category: the category to use for the event
        :regjson string state: the state to use for the event
        :regjson string note: (*optional*) The human readable note describing this Event

        :reqheader Content-Type: The server expects a json body specified with
                                 this header.

        :resheader Location: URL to the created resource.

        :statuscode 201: The Event was successfully created.
        :statuscode 400: The request was malformed.
        :statuscode 401: The request was made without being logged in.
        :statuscode 409: There was a conflict with another resource.
        """

        # we need a unique tx number so we can look these back up again
        # as well as for logging
        # FIXME: how can we guarantee uniqueness here?
        tx = int(time.time() * 100000) + random.randrange(10000, 99999)

        log.info("EVENTS [{}]: Creating events".format(tx))

        try:
            user = self.jbody["user"]
            if not EMAIL_REGEX.match(user):
                user += "@" + self.domain
            event_type_id = self.jbody.get("eventTypeId", None)
            category = self.jbody.get("category", None)
            state = self.jbody.get("state", None)
            note = self.jbody.get("note", None)
        except KeyError as err:
            raise exc.BadRequest(
                "Missing Required Argument: {}".format(err.message)
            )
        except ValueError as err:
            raise exc.BadRequest(err.message)

        if not event_type_id and (not category and not state):
            raise exc.BadRequest(
                "Must specify an event type id or both category and state"
            )

        if event_type_id:
            event_type = self.session.query(EventType).get(event_type_id)
        else:
            event_type = self.session.query(EventType).filter(
                and_(
                    EventType.category == category,
                    EventType.state == state
                )
            ).one()

        if event_type is None:
            self.write_error(400, message="Bad event type")
            return

        category = event_type.category
        state = event_type.state

        hostnames = (
            [self.jbody.get("hostname", None)]
            if self.jbody.get("hostname", None) else []
        )

        if "hostnames" in self.jbody:
            hostnames.extend(self.jbody.get("hostnames"))

        log.info(
            "EVENTS [{}]: Will create event {} {}".format(
                tx, category, state
            )
        )

        log.info(
            "EVENTS [{}]: Hostnames specified: {}".format(
                tx, ", ".join(hostnames)
            )
        )

        # If a host query was specified, we need to talk to the external
        # query server to resolve this into a list of hostnames
        if "hostQuery" in self.jbody:
            query = self.jbody["hostQuery"]
            log.info("EVENTS [{}]: Running query {}".format(tx, query))
            response = PluginHelper.request_get(params={"query": query})
            if response.json()["status"] == "ok":
                hostnames.extend(response.json()["results"])
                log.info(
                    "EVENTS [{}]: Hostnames after query: {}".format(
                        tx, ", ".join(hostnames)
                    )
                )

        # If a quest Id was given, look up the labors in that quest and
        # get all the hostnames for those labors.
        if "questId" in self.jbody:
            log.info("EVENTS [{}]: Looking up quest {}".format(
                tx, self.jbody["questId"])
            )
            quest = self.session.query(Quest).filter_by(
                id=self.jbody["questId"]
            ).scalar()
            if not quest:
                raise exc.NotFound("No such Quest {} found".format(id))
            for labor in quest.labors:
                hostnames.append(labor.host.hostname)

            log.info(
                "EVENTS [{}]: Hostnames after quest expansion: {}".format(
                    tx, ", ".join(hostnames)
                )
            )

        # We need to create a list of hostnames that don't have a Host record
        new_hosts_needed = set(hostnames)
        hosts = (
            self.session.query(Host).filter(Host.hostname.in_(hostnames)).all()
        )

        for host in hosts:
            new_hosts_needed.remove(str(host.hostname))

        # if we need to create hosts, do them all at once
        if new_hosts_needed:
            log.info("EVENTS [{}]: Creating hosts {}".format(
                tx, ", ".join(new_hosts_needed)
            ))
            Host.create_many(self.session, new_hosts_needed)
            hosts = (
                self.session.query(Host).filter(
                    Host.hostname.in_(hostnames)
                ).all()
            )

        if not hosts:
            raise exc.BadRequest("No hosts found with given list")

        try:
            if len(hosts) > 1:
                # if we are supposed to create many events,
                #  we want to do them as a giant batch
                log.info("EVENTS [{}]: Creating multiple events".format(tx))
                events_to_create = []
                for host in hosts:
                    events_to_create.append({
                        "host_id": host.id,
                        "user": user,
                        "event_type_id": event_type.id,
                        "note": note,
                        "tx": tx
                    })
                Event.create_many(self.session, events_to_create, tx)
            else:
                # if we are just creating one event, do it the simple way
                log.info("EVENTS [{}]: Creating 1 event".format(tx))
                event = Event.create(
                    self.session, hosts[0], user, event_type, note=note
                )

        except IntegrityError as err:
            raise exc.Conflict(err.orig.message)
        except exc.ValidationError as err:
            raise exc.BadRequest(err.message)

        log.info("EVENTS [{}]: Flushing and committing".format(tx))
        self.session.flush()
        log.info("EVENTS [{}]: Flushed".format(tx))
        self.session.commit()
        log.info("EVENTS [{}]: Committed".format(tx))

        if len(hosts) == 1:
            json = event.to_dict(self.href_prefix)
            json["href"] = "/api/v1/events/{}".format(event.id)
            self.created(
                "/api/v1/events/{}".format(event.id), json
            )
        else:
            # if we created many events, we need to look them up by the TX
            # number to figure out what they were since the were created in bulk
            created_events = self.session.query(Event).filter(Event.tx == tx).all()
            self.created(
                data={
                    "events": (
                        [event.to_dict(self.href_prefix) for event in created_events]
                    ),
                    "totalEvents": len(created_events)
                }
            )

        log.info("EVENTS [{}]: Created event {} {} for {}".format(
            tx, category, state,
            ", ".join(hostnames)
        ))

    def get(self):
        """**Get all Events**

        **Example Request:**

        .. sourcecode: http

            GET /api/v1/events HTTP/1.1
            Host: localhost

        **Example response:**

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "status": "ok",
                "limit": 10,
                "offset": 0,
                "totalEvents": 10,
                "events": [
                    {
                        "id": 1,
                        "hostId": 1,
                        "timestamp": "2015-06-01 12:11:01",
                        "user": "jonny",
                        "eventTypeId": 1,
                        "note": "Event note",
                    },
                    ...
                ],
            }

        :query int eventTypeId: (*optional/multiple*) Filter Events by EventType id.
        :query int hostId: (*optional*) Filter Events by Host id.
        :query string hostname: (*optional*) Filter Events by Host's hostname
        :query int limit: (*optional*) Limit result to N resources.
        :query int offset: (*optional*) Skip the first N resources.
        :query string after: (*optional*) Only select events at and after a given timestamp
        :query string before: (*optional*) Only select events before a given timestamp
        :query int afterEventType: (*optional*) Only select events at and after the last event of a given event type
        :query string hostQuery: (*optional*) Only select events that match a given host query

        :statuscode 200: The request was successful.
        :statuscode 401: The request was made without being logged in.
        """

        event_type_id = self.get_arguments("eventTypeId")
        host_id = self.get_argument("hostId", None)
        hostname = self.get_argument("hostname", None)
        after_event_type = self.get_argument("afterEventType", None)
        host_query = self.get_argument("hostQuery", None)

        after_time = self.get_argument("after", None)
        if after_time:
            after_time = parser.parse(after_time, yearfirst=True)
            after_time = after_time.replace(tzinfo=None)
            
        before_time = self.get_argument("before", None)
        if before_time:
            before_time = parser.parse(before_time, yearfirst=True)
            before_time = before_time.replace(tzinfo=None)

        events = self.session.query(Event).order_by(desc(Event.timestamp))

        if event_type_id:
            events = events.filter(Event.event_type_id.in_(event_type_id))

        if host_id:
            events = events.filter_by(host_id=host_id)

        found_host = None
        if hostname:
            try:
                found_host = (
                    self.session.query(Host).filter(
                        Host.hostname == hostname
                    ).one()
                )
            except sqlalchemy.orm.exc.NoResultFound:
                raise exc.BadRequest("No host {} found".format(hostname))

            events = events.filter(Event.host == found_host)

        hostnames = []
        if host_query:
            response = PluginHelper.request_get(params={"query": host_query})
            if (
                response.status_code == 200
                and response.json()["status"] == "ok"
            ):
                for hostname in response.json()["results"]:
                    hostnames.append(hostname)
                    logging.info("found host {}".format(hostname))
            else:
                raise exc.BadRequest("Bad host query: {}".format(host_query))

        if hostnames:
            events = (
                events.join(Event.host).filter(Host.hostname.in_(hostnames))
            )

        if after_time:
            logging.info(after_time)
            events = events.filter(Event.timestamp >= after_time)
        if before_time:
            logging.info(before_time)
            events = events.filter(Event.timestamp < before_time)

        if after_event_type:
            # find most recent event of that type for the given host
            # want all events greater than or equal to the time for that event
            subquery = self.session.query(Event).order_by(desc(Event.timestamp)).filter(Event.event_type_id == after_event_type)

            if host_id:
                subquery = subquery.filter_by(host_id=host_id)

            if found_host:
                subquery = subquery.filter(Event.host == found_host)

            if hostnames:
                subquery = (
                    subquery.join(Event.host).filter(Host.hostname.in_(hostnames))
                )

            event = subquery.first()
            if not event:
                raise exc.BadRequest("No event of type {} found".format(after_event_type))
            else:
                events = events.from_self().filter(Event.id >= event.id)

        offset, limit, expand = self.get_pagination_values()
        events, total = self.paginate_query(events, offset, limit)

        events = events.from_self().order_by(Event.timestamp)

        json = {
            "limit": limit,
            "offset": offset,
            "totalEvents": total,
            "events": [
                event.to_dict(base_uri=self.href_prefix, expand=set(expand))
                for event in events.all()
            ],
        }

        self.success(json)


class EventHandler(ApiHandler):
    def get(self, id):
        """**Get a specific Event**

        **Example Request:**

        .. sourcecode:: http

            GET /api/v1/events/1/ HTTP/1.1
            Host: localhost

        **Example response:**

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "status": "ok",
                "id": 1,
                "hostId": 1,
                "timestamp": "2015-06-01 12:11:01",
                "user": "jonny",
                "eventTypeId": 1,
                "note": "Event note",
            }

        :param id: id of the Event to retrieve
        :type id: int

        :query string expand: (*optional*) supports hosts, eventtypes

        :statuscode 200: The request was successful.
        :statuscode 401: The request was made without being logged in.
        :statuscode 404: The EventType was not found.
        """
        offset, limit, expand = self.get_pagination_values()
        event = self.session.query(Event).filter_by(id=id).scalar()
        if not event:
            raise exc.NotFound("No such Event {} found".format(id))

        json = event.to_dict(base_uri=self.href_prefix, expand=expand)

        self.success(json)

    def put(self, id):
        """**Update an Event**

        *Not supported*
        """
        self.not_supported()

    def delete(self, id):
        """**Delete an Event**

        *Not supported*
        """
        self.not_supported()


class FatesHandler(ApiHandler):

    def post(self):
        """**Create a Fate entry**

        **Example Request:**

        .. sourcecode:: http

            POST /api/v1/fates HTTP/1.1
            Host: localhost
            Content-Type: application/json
            {
                "creationEventTypeId": 1,
                "description": "This is a fate",
                "followsId": 1,
                "forCreator": true,
            }

        **Example response:**

        .. sourcecode:: http

            HTTP/1.1 201 OK
            Location: /api/v1/fates/1

            {
                "status": "created",
                "href": "/api/v1/fates/3",
                "id": 3,
                "creationEventTypeId": 1,
                "followsId": 1,
                "precedesIds": [],
                "forCreator": true,
                "description": "This is a fate"
            }

        :reqjson int creationEventTypeId: the ID of the EventType that triggers this Fate
        :regjson int follows: (*optional*) The ID of the Fate this Fate must come after, or null
        :regjson string description: (*optional*) The human readable description this Fate
        :regjson boolean forOwner: (*optional*) Indicates that Labors created by this Fate
                                    would be designated for action by the server owner.
                                    Default: true
        :regjson boolean forCreator: (*optional*) Indicates that Labors created by this Fate
                                    would be designated for action by the Quest owner.
                                    Default: false

        :reqheader Content-Type: The server expects a json body specified with
                                 this header.

        :resheader Location: URL to the created resource.

        :statuscode 201: The Fate was successfully created.
        :statuscode 400: The request was malformed.
        :statuscode 401: The request was made without being logged in.
        :statuscode 409: There was a conflict with another resource.
        """

        try:
            creation_event_type_id = self.jbody["creationEventTypeId"]
            follows_id = self.jbody.get("followsId")
            for_creator = self.jbody.get("forCreator", False)
            for_owner = self.jbody.get("forOwner", True)
            description = self.jbody["description"]
        except KeyError as err:
            raise exc.BadRequest(
                "Missing Required Argument: {}".format(err.message)
            )
        except ValueError as err:
            raise exc.BadRequest(err.message)

        log.info(
            "FATE: Create fate (event-type {}, follows {}, for creator {}, "
            "for owner {}, desc {})".format(
                creation_event_type_id, follows_id,
                for_creator, for_owner, description
            )
        )

        creation_event_type = (
            self.session.query(EventType).get(creation_event_type_id)
        )

        if creation_event_type is None:
            self.write_error(400, message="Bad creation event type")
            return

        try:
            fate = Fate.create(
                self.session, creation_event_type,
                follows_id=follows_id, for_creator=for_creator,
                for_owner=for_owner,
                description=description
            )
        except IntegrityError as err:
            raise exc.Conflict(err.orig.message)
        except exc.ValidationError as err:
            raise exc.BadRequest(err.message)

        self.session.commit()

        json = fate.to_dict(self.href_prefix)
        json["href"] = "/api/v1/fates/{}".format(fate.id)

        self.created("/api/v1/fates/{}".format(fate.id), json)

        log.info(
            "FATE: Created fate {} (event-type {}, follows {}, "
            "for creator {}, for owner {}, desc {})".format(
                fate.id,
                creation_event_type_id, follows_id,
                for_creator, for_owner, description
            )
        )

    def get(self):
        """**Get all Fates**

        **Example Request:**

        .. sourcecode:: http

            GET /api/v1/fates HTTP/1.1
            Host: localhost

        **Example response:**

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "limit": 10,
                "offset": 0,
                "totalFates": 3,
                "fates": [
                    {
                        "id": 1,
                        "href": "/api/v1/fates/1",
                        "creationEventTypeId": 1,
                        "followsId": null,
                        "precedesIds": [],
                        "forCreator": 0,
                        "precedesIds": [3, 5],
                        "description": "This is a fate",
                    },
                    ...
                ],
            }

        :query int limit: (*optional*) Limit result to N resources.
        :query int offset: (*optional*) Skip the first N resources.

        :query string expand: (*optional*) supports eventtypes

        :statuscode 200: The request was successful.
        :statuscode 401: The request was made without being logged in.
        """
        fates = self.session.query(Fate).order_by(Fate.id)

        offset, limit, expand = self.get_pagination_values()
        fates, total = self.paginate_query(fates, offset, limit)

        fates_json = [
            fate.to_dict(base_uri=self.href_prefix, expand=set(expand))
            for fate in fates.all()
        ]

        json = {
            "limit": limit,
            "offset": offset,
            "totalFates": total,
            "fates": fates_json,
        }

        self.success(json)


class FateHandler(ApiHandler):
    def get(self, id):
        """**Get a specific Fate**

        **Example Request:**

        .. sourcecode:: http

            GET /api/v1/fates/1/ HTTP/1.1
            Host: localhost

        **Example response:**

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "status": "ok",
                "id": 1,
                "href": "/api/v1/fates/1",
                "creationEventTypeId": 1,
                "followsId": null,
                "precedesIds": [],
                "forCreator": false,
                "forOwner": true,
                "description": string,
            }

        :param id: id of the Fate to retrieve
        :type id: int

        :query string expand: (*optional*) supports eventtypes

        :statuscode 200: The request was successful.
        :statuscode 401: The request was made without being logged in.
        :statuscode 404: The Fate was not found.
        """
        offset, limit, expand = self.get_pagination_values()
        fate = self.session.query(Fate).filter_by(id=id).scalar()
        if not fate:
            raise exc.NotFound("No such Fate {} found".format(id))

        json = fate.to_dict(base_uri=self.href_prefix, expand=set(expand))

        self.success(json)

    def put(self, id):
        """**Update a Fate**

        **Example Request:**

        .. sourcecode:: http

            PUT /api/v1/fates/3 HTTP/1.1
            Host: localhost
            Content-Type: application/json

            {
                "description": "New desc",
                "followsId": 1
            }

        **Example response:**

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "status": "ok",
                "id": 3,
                "href": "/api/v1/fates/3",
                "creationEventTypeId": 1,
                "followsId": 1,
                "precedesId": [],
                "forCreator": false,
                "forOwner": true
                "description": "New desc"
            }

        :param id: id of the Fate that should be updated.
        :type id: string

        :reqjson string description: The new description of this Fate.
        :reqjson boolean intermediate: The new intermediate flag value.

        :reqheader Content-Type: The server expects a json body specified with
                                 this header.

        :statuscode 200: The request was successful.
        :statuscode 400: The request was malformed.
        :statuscode 401: The request was made without being logged in.
        :statuscode 403: The request was made with insufficient permissions.
        :statuscode 404: The Fate was not found.
        :statuscode 409: There was a conflict with another resource.
        """

        log.info("FATE: Update {}".format(id))

        fate = self.session.query(Fate).filter_by(id=id).scalar()
        if not fate:
            raise exc.NotFound("No such Fate {} found".format(id))

        try:
            if "description" in self.jbody:
                fate = fate.update(description=self.jbody["description"])
            if "followsId" in self.jbody:
                fate = fate.update(follows_id=self.jbody['followsId'])

        except IntegrityError as err:
            raise exc.Conflict(str(err.orig))

        json = fate.to_dict(self.href_prefix)

        self.success(json)

    def delete(self, id):
        """**Delete a Fate**

        *Not supported*
        """
        self.not_supported()


class LaborsHandler(ApiHandler):

    def post(self):
        """**Create a Labor entry**

        *Not supported.  Labors are only created by Fates.*
        """
        self.not_supported()

    def get(self):
        """**Get all Labors**

        **Example Request:**

        .. sourcecode:: http

            GET /api/v1/labors HTTP/1.1
            Host: localhost

        **Example response:**

        .. sourcecode:: http

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
                        "startingLaborId": null,
                        "href": "/api/v1/labors/23",
                        "for_owner": false,
                        "for_creator": true,
                        "questId": 5,
                        "hostId": 26,
                        "creationTime": timestamp,
                        "ackTime": timestamp,
                        "targetTime": timestamp
                        "ackUser": string,
                        "completionTime": timestamp,
                        "creationEventId": 127,
                        "completionEventId": 212,
                    },
                    ...
                ],
            }

        :query string hostname: (*optional*) filter Labors by a particular hostname
        :query string startingLaborId: (*optional*) get Labors by the Id or the Id of the starting labor
        :query string hostQuery: (*optional*) the query to send to the plugin to come up with the list of hostnames
        :query string userQuery: (*optional*) get labors for machines owned by this user or for which this user is responsible
        :query string category: (*optional*) limit labors to ones where the starting event type is of this category
        :query string state: (*optional*) limit labors to ones where the starting event type is of this state
        :query boolean open: if true, filter Labors to those still open
        :query int questId: the id of the quest we want to filter by
        :query string expand: (*optional*) supports hosts, eventtypes, events, quests
        :query int limit: (*optional*) Limit result to N resources.
        :query int offset: (*optional*) Skip the first N resources.

        :statuscode 200: The request was successful.
        :statuscode 401: The request was made without being logged in.
        """
        hostname = self.get_argument("hostname", None)
        starting_labor_id = self.get_argument("startingLaborId", None)
        open_flag = self.get_argument("open", None)
        quest_id = self.get_argument("questId", None)
        host_query = self.get_argument("hostQuery", None)
        user_query = self.get_argument("userQuery", None)
        category = self.get_argument("category", None)
        state = self.get_argument("state", None)

        labors = self.session.query(Labor)

        # if filtering by category or state, find the event types that match
        # these conditions and add them to the query
        if category or state:
            event_types = self.session.query(EventType)
            if category:
                event_types = event_types.filter(
                    EventType.category == category
                )
            if state:
                event_types = event_types.filter(
                    EventType.state == state
                )
            valid_event_types = [event_type.id for event_type in event_types]
            labors = labors.join(Labor.creation_event).join(Event.event_type).filter(
                EventType.id.in_(valid_event_types)
            )

        # if specifying to filter by open or closed state, add that to the query
        if open_flag and open_flag.lower() == "true":
            labors = labors.filter(Labor.completion_event_id == None)
        if open_flag and open_flag.lower() == "false":
            labors = labors.filter(Labor.completion_event_id != None)

        if quest_id:
            labors = labors.filter(Labor.quest_id == quest_id)

        if starting_labor_id:
            labors = labors.filter(or_(
                Labor.id == starting_labor_id,
                Labor.starting_labor_id == starting_labor_id
            ))

        # if user wants to filter by a specific host, verify that the host is
        # good and add that to the query
        if hostname is not None:
            try:
                host = (
                    self.session.query(Host).filter(
                        Host.hostname == hostname
                    ).one()
                )
            except sqlalchemy.orm.exc.NoResultFound:
                raise exc.BadRequest("No host {} found".format(hostname))

            labors = (
                labors.filter(Labor.host == host)
                .order_by(desc(Labor.creation_time))
            )

        # if the user specified a host query, we need to translate that into a
        # list of hostnames to use.
        host_query_hostnames = []
        if host_query:
            response = PluginHelper.request_get(params={"query": host_query})
            if (
                response.status_code == 200
                and response.json()["status"] == "ok"
            ):
                # FIXME -- couldn't this just be hostnames.extend?
                for hostname in response.json()["results"]:
                    host_query_hostnames.append(hostname)
            else:
                raise exc.BadRequest("Bad host query: {}".format(host_query))

        # if the user wants to filter by user, let's first find the hostnames
        # of machines the user would be responsible for
        user_query_hostnames = []
        user_created_quests = []
        if user_query:
            response = PluginHelper.request_get(params={"user": user_query})
            if (
                response.status_code == 200
                and response.json()["status"] == "ok"
            ):
                for hostname in response.json()["results"]:
                    user_query_hostnames.append(hostname)
            else:
                raise exc.BadRequest("Bad user query: {}".format(user_query))

            user_created_quests =[
                quest.id for quest in
                (
                    self.session.query(Quest).filter(
                        Quest.creator == user_query
                    ).all()
                )
            ]

        # since we may have used multiple ways to get hostname lists, compile
        # into a final list of hostnames we care about
        hostnames = []
        if host_query and user_query:
            hostnames = list(
                set(host_query_hostnames) & set(user_query_hostnames)
            )
        elif host_query:
            hostnames = host_query_hostnames
        elif user_query:
            hostnames = user_query_hostnames

        # if we are just doing a simple host_query, we can just filter by
        # the hostnames we collected.  Otherwise, if we are doing a user_query
        # we need not just hosts owned by the user, but also labors that belong
        # to a quest creator that matches the user name
        if host_query or user_query:
            if not hostnames:
                raise exc.BadRequest("Querying on 0 hosts")

            hosts = (
                self.session.query(Host).filter(
                    Host.hostname.in_(hostnames)
                )
            )
            host_ids = [host.id for host in hosts]
            if not user_query:
                labors = labors.filter(and_(
                    Labor.host_id.in_(host_ids),
                    Labor.for_owner == 1
                ))
            elif hostnames and user_query:
                labors = labors.filter(or_(
                    and_(
                        Labor.host_id.in_(host_ids),
                        Labor.for_owner == 1
                    ),
                    and_(
                        Labor.for_creator == 1,
                        Labor.quest_id.in_(user_created_quests)
                    )
                ))

        offset, limit, expand = self.get_pagination_values()
        labors, total = self.paginate_query(labors, offset, limit)

        labors = labors.from_self().order_by(Labor.creation_time)

        json = {
            "limit": limit,
            "offset": offset,
            "totalLabors": total,
            "labors": [
                labor.to_dict(
                    base_uri=self.href_prefix, expand=set(expand)
                ) for labor in labors
            ],
        }

        self.success(json)


class LaborHandler(ApiHandler):
    def get(self, id):
        """**Get a specific Labor**

        **Example Request:**

        .. sourcecode:: http

            GET /api/v1/labors/1 HTTP/1.1
            Host: localhost

        **Example response:**

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "status": "ok",
                "id": 23,
                "startingLaborId": null,
                "questId": 5,
                "hostId": 26,
                "for_creator": true,
                "for_owner": false,
                "creationTime": timestamp,
                "targetTime": timestamp,
                "ackTime": timestamp,
                "ackUser": string,
                "completionTime": timestamp,
                "creationEventId": 127,
                "completionEventId": 212,
            }

        :param id: id of the Labor to retrieve
        :type id: int

        :query string expand: (*optional*) supports hosts, eventtypes

        :statuscode 200: The request was successful.
        :statuscode 401: The request was made without being logged in.
        :statuscode 404: The EventType was not found.
        """
        offset, limit, expand = self.get_pagination_values()
        labor = self.session.query(Labor).filter_by(id=id).scalar()
        if not labor:
            raise exc.NotFound("No such Labor {} found".format(id))

        self.success(
            labor.to_dict(base_uri=self.href_prefix, expand=expand)
        )

    def put(self, id):
        """**Update a Labor**

        **Example Request:**

        .. sourcecode:: http

            PUT /api/v1/labors/23 HTTP/1.1
            Host: localhost
            Content-Type: application/json

            {
                "questId": 1,
            }

        or

        .. sourcecode:: http

            {
                "ackUser": "johnny"
            }

        **Example response:**

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "status": "ok",
                "id": 23,
                "questId": 1,
                "hostId": 26,
                "creationTime": timestamp,
                "targetTime": timestamp,
                "ackTime": timestamp,
                "ackUser": "johnny",
                "completionTime": timestamp,
                "creationEventId": 127,
                "completionEventId": 212,
            }

        :param id: id of the Labor that should be updated.
        :type id: string

        :reqjson int questId: The Quest ID to which this Fate should now be associated.
        :reqjson string ackUser: The username to log as having acknowledged this Labor

        :reqheader Content-Type: The server expects a json body specified with
                                 this header.

        :statuscode 200: The request was successful.
        :statuscode 400: The request was malformed.
        :statuscode 401: The request was made without being logged in.
        :statuscode 403: The request was made with insufficient permissions.
        :statuscode 404: The Labor was not found.
        :statuscode 409: There was a conflict with another resource.
        """

        log.info("LABOR: Update {}".format(id))

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
                if not EMAIL_REGEX.match(ack_user):
                    ack_user += "@" + self.domain

            if not quest_id and not ack_user:
                raise exc.BadRequest("Must update either questId or ackUser")
        except KeyError as err:
            raise exc.BadRequest(
                "Missing Required Argument: {}".format(err.message)
            )

        try:
            if quest_id:
                labor.update(quest_id=quest_id)
            if ack_user:
                labor.acknowledge(ack_user)
        except IntegrityError as err:
            raise exc.Conflict(str(err.orig))

        json = labor.to_dict(self.href_prefix)

        self.success(json)

        log.info("LABOR: Updated {}: {} {}".format(
            id,
            "quest is now {}".format(quest_id) if quest_id else "",
            "acked by user {}".format(ack_user) if ack_user else ""
        ))

    def delete(self, id):
        """**Delete a Labor**

        *Not supported*
        """
        self.not_supported()


class QuestsHandler(ApiHandler):
    def post(self):
        """**Create a Quest entry**

        **Example Request:**

        .. sourcecode:: http

            POST /api/v1/quests HTTP/1.1
            Host: localhost
            Content-Type: application/json
            {
                "fateId": 1,
                "creator": "johnny",
                "targetTime": timestamp,
                "description": "This is a quest almighty",
                "hostnames": [],
                "hostQuery": "tag=value"
            }

        **Example response:**

        .. sourcecode:: http

            HTTP/1.1 201 OK
            Location: /api/v1/hosts/example

            {
                "status": "created",
                "id": 1,
                "href": "/api/v1/quests/1",
                "creator": "johnny",
                "embarkTime": timestamp,
                "targetTime": timestamp,
                "completionTime": timestamp,
                "description": "This is a quest almighty",
                "labors": [],
            }

        :reqjson int eventTypeId: the ID of the EventType to for the Events that will be thrown in the creation of this Quest
        :regjson string creator: the user creating this Quest
        :regjson array hostnames: the array of hostnames that will be part of this Quest
        :regjson string hostQuery: the query to send to the plugin to come up with the list of hostnames that will be part of this Quest
        :regjson string description: The human readable description this Quest
        :regjson timestamp targetTime: (*optional*) The target date for the completion of this Quest

        :reqheader Content-Type: The server expects a json body specified with
                                 this header.

        :resheader Location: URL to the created resource.

        :statuscode 201: The Quest was successfully created.
        :statuscode 400: The request was malformed.
        :statuscode 401: The request was made without being logged in.
        :statuscode 409: There was a conflict with another resource.

        """

        tx = id_generator()

        log.info("QUEST [{}]: Creating a new quest".format(tx))

        try:
            fate_id = self.jbody["fateId"]
            creator = self.jbody["creator"]
            if not EMAIL_REGEX.match(creator):
                creator += "@" + self.domain
            description = self.jbody["description"]
            hostnames = self.jbody.get("hostnames") or []

            if "targetTime" in self.jbody:
                target_time = parser.parse(
                    self.jbody["targetTime"]
                )
                target_time = target_time.replace(tzinfo=None)
                if target_time <= datetime.utcnow():
                    raise exc.BadRequest(
                        "Quest target date must be in future"
                    )
            else:
                target_time = None
        except KeyError as err:
            raise exc.BadRequest(
                "Missing Required Argument: {}".format(err.message)
            )
        except ValueError as err:
            raise exc.BadRequest(err.message)

        log.info(
            "QUEST [{}]: {} creating quest with fate {} for hosts {}".format(
                tx, creator, fate_id, ", ".join(hostnames)
            )
        )

        fate = (
            self.session.query(Fate).get(fate_id)
        )

        if fate is None:
            self.write_error(400, message="Bad fate id {}".format(fate_id))
            return

        # If a host query was specified, we need to talk to the external
        # query server to resolve this into a list of hostnames
        if "hostQuery" in self.jbody:
            query = self.jbody["hostQuery"]
            response = PluginHelper.request_get(params={"query": query})
            if response.json()["status"] == "ok":
                hostnames.extend(response.json()["results"])
                log.info(
                    "QUEST [{}]: Hostnames after query: {}".format(
                        tx, ", ".join(hostnames)
                    )
                )

        # We need to create a list of hostnames that don't have a Host record
        new_hosts_needed = list(hostnames)
        hosts = (
            self.session.query(Host).filter(Host.hostname.in_(hostnames)).all()
        )
        for host in hosts:
            new_hosts_needed.remove(str(host.hostname))

        # if we need to create hosts, do them all at once
        if new_hosts_needed:
            Host.create_many(self.session, new_hosts_needed)
            hosts = (
                self.session.query(Host).filter(
                    Host.hostname.in_(hostnames)
                ).all()
            )

        log.info("QUEST [{}]: Working with {} hosts".format(tx, len(hosts)))

        if len(hosts) == 0:
            raise exc.BadRequest("No hosts found with given list")

        try:
            quest = Quest.create(
                self.session, creator, hosts, target_time, fate_id=fate_id,
                description=description
            )
        except IntegrityError as err:
            raise exc.Conflict(err.orig.message)
        except exc.ValidationError as err:
            raise exc.BadRequest(err.message)

        self.session.flush()
        self.session.commit()

        json = quest.to_dict(self.href_prefix)

        json["labors"] = (
            [labor.to_dict(self.href_prefix)
             for labor in quest.get_open_labors()]
        )

        self.created("/api/v1/quests/{}".format(quest.id), json)

        log.info(
            "QUEST [{}]: Created quest {}".format(tx, quest.id)
        )

    def get(self):
        """**Get all Quests**

        **Example Request:**

        .. sourcecode:: http

            GET /api/v1/quests?progressInfo=true HTTP/1.1
            Host: localhost

        **Example response:**

        .. sourcecode:: http

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
                        "href": "/api/v1/quests/1",
                        "creator": "johnny",
                        "embarkTime": timestamp,
                        "targetTime": timestamp,
                        "completionTime": timestamp,
                        "description": "This is a quest almighty",
                        "totalLabors": 20,
                        "openLabors": 10,
                        "percentComplete": 50,
                        "labors": [],
                    },
                    ...
                ],
            }

        :query boolean filterClosed: (*optional*) if true, filter out completed Quests
        :query boolean progressInfo: (*optional*) if true, include progress information
        :query string byCreator: (*optional*) if set, filter the quests by a particular creator
        :query string hostnames: (*optional*) filter to quests that pertain to a particular host
        :query string hostQuery: (*optional*) filter quests to those involving hosts returned by the external query
        :query int limit: (*optional*) Limit result to N resources.
        :query int offset: (*optional*) Skip the first N resources.

        :statuscode 200: The request was successful.
        :statuscode 401: The request was made without being logged in.
        """
        filter_closed = self.get_argument("filterClosed", None)
        progress_info = self.get_argument("progressInfo", None)
        by_creator = self.get_argument("byCreator", None)
        hostnames = self.get_argument("hostnames", None)
        host_query = self.get_argument("hostQuery", None)

        if hostnames:
            hostnames = hostnames.split(",")
        else:
            hostnames = []

        if host_query:
            response = PluginHelper.request_get(params={"query": host_query})
            if (
                response.status_code == 200
                and response.json()["status"] == "ok"
            ):
                for hostname in response.json()["results"]:
                    hostnames.append(hostname)
            else:
                raise exc.BadRequest("Bad host query: {}".format(host_query))

        # We used to sort in reverse embark time so that the default would be
        # to show the latest quests but we don't want to do that anymore
        # quests = self.session.query(Quest).order_by(desc(Quest.embark_time))
        quests = self.session.query(Quest).order_by(Quest.embark_time)

        if hostnames:
            quests = (
                quests.join(Quest.labors).join(Labor.host)
                .filter(Host.hostname.in_(hostnames))
            ).group_by(Quest)

        if filter_closed:
            quests = quests.filter(Quest.completion_time == None)

        if by_creator:
            quests = quests.filter(Quest.creator == by_creator)

        offset, limit, expand = self.get_pagination_values()
        quests, total = self.paginate_query(quests, offset, limit)

        quests = quests.from_self().order_by(Quest.embark_time)

        quests_json = []
        for quest in quests.all():
            quest_json = quest.to_dict(
                base_uri=self.href_prefix,
                expand=set(expand)
            )
            if progress_info:
                quest_json = quest.calculate_progress(quest_json)
            quests_json.append(quest_json)

        json = {
            "limit": limit,
            "offset": offset,
            "totalQuests": total,
            "quests": quests_json
        }

        self.success(json)


class QuestHandler(ApiHandler):
    def get(self, id):
        """**Get a specific Quest**

        **Example Request:**

        .. sourcecode:: http

            GET /api/v1/quests/1 HTTP/1.1
            Host: localhost

        **Example response:**

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "status": "ok",
                "id": 1,
                "href": "/api/v1/quests/1",
                "creator": "johnny",
                "embarkTime": timestamp,
                "targetTime": timestamp,
                "completionTime": timestamp,
                "description": "This is a quest almighty",
                "labors": [],
            }

        :param id: id of the Quest to retrieve
        :type id: int

        :query string expand: (*optional*) supports labors, hosts, events, eventtypes
        :query boolean progressInfo: (*optional*) if true, include progress information
        :query boolean onlyOpenLabors: (*optional*) if true, only return open labors

        :statuscode 200: The request was successful.
        :statuscode 401: The request was made without being logged in.
        :statuscode 404: The EventType was not found.
        """
        offset, limit, expand = self.get_pagination_values()

        progress_info = self.get_argument("progressInfo", False)
        only_open_labors = self.get_argument("onlyOpenLabors", False)

        quest = self.session.query(Quest).filter_by(id=id).scalar()

        if not quest:
            raise exc.NotFound("No such Quest {} found".format(id))

        out = quest.to_dict(
            base_uri=self.href_prefix, expand=set(expand),
            only_open_labors=only_open_labors
        )

        if progress_info:
            out = quest.calculate_progress(out)

        self.success(out)

    def put(self, id):
        """**Update a Quest**

        **Example Request:**

        .. sourcecode:: http

             PUT /api/v1/quest/1 HTTP/1.1
             Host: localhost
             Content-Type: application/json

             {
                 "description": "New desc",
                 "creator": "tammy"
             }

        **Example response:**

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "status": "ok",
                "id": 1,
                "href": "/api/v1/quests/1",
                "creator": "tammy",
                "embarkTime": timestamp,
                "targetTime": timestamp,
                "completionTime": timestamp,
                "description": "New desc",
                "labors": [],
            }

        :param id: id of the Quest that should be updated.
        :type id: string

        :reqjson string description: the new description of the Quest
        :reqjson string creator: The new username of the creator (owner)
        :regjson timestamp targetTime: Set a new targetTime

        :reqheader Content-Type: The server expects a json body specified with
                                 this header.

        :statuscode 200: The request was successful.
        :statuscode 400: The request was malformed.
        :statuscode 401: The request was made without being logged in.
        :statuscode 403: The request was made with insufficient permissions.
        :statuscode 404: The Quest was not found.
        :statuscode 409: There was a conflict with another resource.
        """

        log.info("QUEST: Updating {}".format(id))

        quest = self.session.query(Quest).filter_by(id=id).scalar()

        if not quest:
            raise exc.NotFound("No such Quest {} found".format(id))

        new_desc = None
        new_creator = None
        new_target_time = None
        try:
            if "description" in self.jbody:
                new_desc = self.jbody["description"]
            if "creator" in self.jbody:
                new_creator = self.jbody['creator']
                if not EMAIL_REGEX.match(new_creator):
                    new_creator += "@" + self.domain
            if "targetTime" in self.jbody:
                new_target_time = parser.parse(
                    self.jbody["targetTime"]
                )
                new_target_time = new_target_time.replace(tzinfo=None)
                if new_target_time <= datetime.utcnow():
                    raise exc.BadRequest(
                        "Quest target date must be in future"
                    )
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
            if new_target_time:
                quest = quest.update(
                    target_time=new_target_time
                )

        except IntegrityError as err:
            raise exc.Conflict(str(err.orig))

        json = quest.to_dict(self.href_prefix)

        self.success(json)

        log.info("QUEST [{}]: Updated: {} {} {}".format(
            id,
            "new description {}".format(new_desc) if new_desc else "",
            "new creator {}".format(new_creator) if new_creator else "",
            "new target time {}".format(new_target_time) if new_target_time else ""
        ))

    def delete(self, id):
        """**Delete a Quest**

        *Not supported*
        """
        self.not_supported()


class ExtQueryHandler(ApiHandler):
    def get(self):
        """**Get results from the external query services**

        The frontend will need to run queries against the external query server
        so that users can validate the results before working with a particular
        query.  This handler acts as a passthrough so users can do exactly that.

        **Example Request:**

        .. sourcecode:: http

            GET /api/v1/query?query=server HTTP/1.1
            Host: localhost

        **Example response:**

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "status": "ok",
                "results": [
                    {
                        "id": 1,
                        "href": "/api/v1/hosts/server1",
                        "hostname": "server1",
                    },
                    ...
                ]
            }

        :statuscode 200: The request was successful.
        :statuscode 401: The request was made without being logged in.
        """

        response = PluginHelper.request_get(params=self.request.arguments)
        if (
            response.status_code == 200
            and response.json()["status"] == "ok"
        ):
            result_json = {
                "results": response.json()["results"],
            }
        else:
            raise exc.BadRequest("Bad host query: {}".format(
                self.request.arguments
            ))

        self.success(result_json)

    def post(self):
        """
        Pass through post to the external query handler
        """

        json_data = json.loads(self.request.body)
        response = PluginHelper.request_post(json_body=json_data)
        if (
            response.status_code == 200
            and response.json()["status"] == "ok"
        ):
            result_json = {
                "results": response.json()["results"],
            }
        else:
            raise exc.BadRequest("Bad host query: {}".format(
                self.request.body
            ))

        self.success(result_json)


class CurrentUserHandler(ApiHandler):
    def get(self):
        """ **Get a current authenticated user**

        **Example Request**:

        .. sourcecode:: http

            GET /api/v1/currentUser HTTP/1.1
            Host: localhost

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "status": "ok",
                "user": "user@example.com"
            }

        :statuscode 200: The request was successful.
        :statuscode 401: The request was made without being logged in.
        :statuscode 403: The request was made with insufficient permissions.
        :statuscode 404: The User was not found.
        """

        user = None
        if self.request.headers.get('X-Pp-User'):
            user = self.request.headers['X-Pp-User']

        result_json = {
            "user": user
        }

        self.success(result_json)


class ServerConfig(ApiHandler):
    def get(self):
        """ **Get the server's configuration information**

        This is used to get the config information that the front end might
        want to know about.

        **Example Request**:

        .. sourcecode:: http

            GET /api/v1/serverConfig HTTP/1.1
            Host: localhost

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "status": "ok",
                "domain": "example.com"
            }
        """
        result_json = {
            "domain": settings.domain,
            "fullstoryId": settings.fullstory_id
        }

        self.success(result_json)


class QuestMailHandler(ApiHandler):
    def post(self, id):
        """**Send a message to all owners that are involved with a quest**

        **Example Request:**

        .. sourcecode:: http

            POST /api/v1/quest/20/mail HTTP/1.1
            Host: localhost
            Content-Type: application/json
            {
                "serverOwners": true,
                "laborOwners": false,
                "from": "user@example.com",
                "subject": "Hello!",
                "message": "Work is about to commence."
            }

        **Example response:**

        .. sourcecode:: http

            HTTP/1.1 201 OK
            Location: /api/v1/hosts/example

            {
                "status": "created",
            }

        **Note:**
        Hermes will automatically append a link to the quest so users can go there directly from the email

        :param id the ID of the quest we are working with when sending an email
        :regjson boolean serverOwners: send to all owners of servers that have labors in this quest
        :regjson boolean laborOwners: send to all labor owners (e.g. server owners if they own the active labor or the quest owner if they own the active labor)
        :regjson string from: the sender email address
        :regjson string subject: the subject line of the email
        :regjson string message: the body of the message

        :reqheader Content-Type: The server expects a json body specified with
                                 this header.

        :statuscode 201: Email was created and sent

        """

        server_owners = self.jbody.get('serverOwners', False)
        labor_owners = self.jbody.get('laborOwners', False)

        if not server_owners and not labor_owners:
            raise exc.BadRequest(
                "Must specify serverOwners and/or laborOwners as true"
            )

        log.info(
            "QUEST [{}]: sent email to {}{}{}".format(
                id,
                "server owners" if server_owners else "",
                " and " if server_owners and labor_owners else "",
                "labor owners" if labor_owners else ""
            )
        )

        try:
            from_address = self.jbody['from']
            subject = self.jbody['subject']
            message = self.jbody['message']
        except KeyError as err:
            raise exc.BadRequest(
                "Missing Required Argument: {}".format(err.message)
            )
        except ValueError as err:
            raise exc.BadRequest(err.message)

        # Open the quest and grab the labors
        quest = self.session.query(Quest).get(id)
        if not quest:
            raise exc.NotFound(
                "Quest {} not found".format(id)
            )

        labors = quest.labors
        # Grab the hostnames and look up the owners
        hostnames = set()
        for labor in labors:
            hostnames.add(labor.host.hostname)

        # get the owner information
        try:
            results = PluginHelper.request_post(
                json_body={
                    "operation": "owners",
                    "hostnames": list(hostnames)
                }
            )
            owners = results.json()['results']
        except Exception as e:
            logging.error("Failed to get host owners: " + e.message)
            raise exc.BadRequest(
                "Host owners not found"
            )

        # get contact information from strongpoc
        strongpoc_contacts = None
        if settings.strongpoc_server:
            # get the contact information
            try:
                results = PluginHelper.request_get(
                    path = "/api/pocs/?expand=teams&expand=service_providers&expand=contact_types&service_provider__name=hermes&contact_type__name=email",
                    server = settings.strongpoc_server
                )
                strongpoc_results = results.json()
                strongpoc_contacts = {}
                for result in strongpoc_results:
                    strongpoc_contacts[result['team']['name']] = result['value']
            except Exception as e:
                logging.error("Failed to get strongpoc contacts: " + e.message)

        recipients = set()

        # If we want labor owners, loop through and see if who that should
        # be and add them to recipients
        if labor_owners:
            for labor in labors:
                if labor.for_creator:
                    # add quest creator to recipients
                    recipients.add(quest.creator)
                if labor.for_owner:
                    # add machine owner to recipients
                    owner = owners[labor.host.hostname]
                    if strongpoc_contacts and  owner in strongpoc_contacts:
                        recipients.add(strongpoc_contacts[owner])
                    else:
                        recipients.add("{}@{}".format(owner, settings.domain))

        # If we want server owners, loop through hosts
        # and add owners to the list
        if server_owners:
            for labor in labors:
                # add machine owner to recipients
                owner = owners[labor.host.hostname]
                if strongpoc_contacts and owner in strongpoc_contacts:
                    recipients.add(strongpoc_contacts[owner])
                else:
                    recipients.add("{}@{}".format(owner, settings.domain))

        # Send email
        email_message(recipients, subject, message, sender=from_address)

        self.created()

        log.info(
            "QUEST [{}]: sent email to {}{}{}".format(
                id,
                "server owners" if server_owners else "",
                " and " if server_owners and labor_owners else "",
                "labor owners" if labor_owners else ""
            )
        )
