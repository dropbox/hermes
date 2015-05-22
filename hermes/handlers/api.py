import ipaddress
import logging
from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError


from .util import ApiHandler
from .. import exc
from ..models import Host
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
            Location: /api/hosts/example

            {
                "status": "ok",
                "data": {
                    "host": {
                        "id": 1,
                        "hostname": "example"
                    }
                }
            }
        """

        try:
            hostname = self.jbody["name"]
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

        json = host.to_dict("/api/v1")
        json['href'] = "/api/v1/hosts/{}".format(host.hostname)

        self.created("/api/v1/hosts/{}".format(host.id), json)

    def get(self):
        """ Get all Hosts

        Example Request:

            GET /api/hosts HTTP/1.1
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
        hostname = self.get_argument("name", None)

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

            GET /api/hosts/example HTTP/1.1
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
        for labor in host.get_labors().limit(limit).offset(offset).all():
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
                host.get_latest_events().limit(limit).offset(offset).all()
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

            PUT /api/hosts/example HTTP/1.1
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
                self.current_user.id,
                hostname=hostname,
            )
        except IntegrityError as err:
            raise exc.Conflict(str(err.orig))

        self.success({
            "host": host.to_dict("/api/v1"),
        })

    def delete(self, hostname):
        """Delete a Host

        Example Request:

            DELETE /api/hosts/example HTTP/1.1
            Host: localhost

        Example response:

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "status": "ok",
                "data": {
                    "message": Site hostname deleted."
                }
            }

        """
        host = self.session.query(Host).filter_by(hostname=hostname).scalar()
        if not host:
            raise exc.NotFound("No such Host {} found".format(hostname))

        try:
            host.delete(self.current_user.id)
        except IntegrityError as err:
            raise exc.Conflict(err.orig.message)

        self.success({
            "message": "Host {} deleted.".format(hostname),
        })
