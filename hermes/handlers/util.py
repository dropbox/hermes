import json
import logging
import requests
import sys
from tornado.web import RequestHandler, urlparse, HTTPError
from tornado.escape import utf8
from werkzeug.http import parse_options_header

from .. import exc
from .. import models
from ..settings import settings


# Logging object
log = logging.getLogger(__name__)

# If raven library is available, modify the base handler to support Sentry.
try:
    from raven.contrib.tornado import SentryMixin
except ImportError:
    pass
else:
    class SentryHandler(SentryMixin, RequestHandler):
        pass
    RequestHandler = SentryHandler


API_VER = "/api/v1"

class PluginHelper(object):
    @classmethod
    def request_get(cls, path="", params={}):
        """Make an HTTP GET request for the given path

        Args:
            path: the full path to the resource
        Returns:
            the http response
        """
        response = requests.get(settings.query_server + path, params=params)

        return response


class BaseHandler(RequestHandler):
    def initialize(self):

        my_settings = self.application.my_settings

        # Lazily build the engine and session for support of multi-processing
        if my_settings.get("db_engine") is None:
            my_settings["db_engine"] = models.get_db_engine(my_settings.get("db_uri"))
            models.Session.configure(bind=my_settings["db_engine"])
            my_settings["db_session"] = models.Session

        self.engine = my_settings.get("db_engine")
        self.session = my_settings.get("db_session")()
        self.domain = my_settings.get("domain")

    def on_finish(self):
        self.session.close()

    def get_current_user(self):
        """Default global user fetch by user_auth_header."""

        # Fetch the email address from the auth_header (e.g. X-Hermes-Email)
        auth_header = settings.user_auth_header
        log.debug('  fetching auth_header: %s' % auth_header)
        email = self.request.headers.get(auth_header)

        if email is not None:
            log.debug('auth_header authenticated user: %s' % email)
            return email
        return None

    def prepare(self):
        log.debug('BaseHandler.prepare()')


class FeHandler(BaseHandler):

    def prepare(self):
        BaseHandler.prepare(self)
        # Need to access token to set Cookie.
        # self.xsrf_token

    def render(self, template_name, **kwargs):
        context = {}
        context.update(self.get_template_namespace())
        context.update(kwargs)
        self.write("Nothing to see here.")

    def write_error(self, status_code, **kwargs):
        message = "An unknown problem has occured :("
        if "exc_info" in kwargs:
            inst = kwargs["exc_info"][1]
            if isinstance(inst, HTTPError):
                message = inst.log_message
            else:
                message = str(inst)

        # Pass context to the error template
        self.render("error.html", code=status_code, message=message)


class ApiHandler(BaseHandler):
    def initialize(self):
        BaseHandler.initialize(self)
        self._jbody = None
        self.href_prefix = None

    @property
    def jbody(self):
        if self._jbody is None:
            if self.request.body:
                self._jbody = json.loads(self.request.body)
            else:
                self._jbody = {}
        return self._jbody

    def get_pagination_values(self, max_limit=None):
        if self.get_arguments("limit"):
            if self.get_arguments("limit")[0] == "all":
                limit = None
            else:
                limit = int(self.get_arguments("limit")[0])
        else:
            limit = 10
        offset = int((self.get_arguments("offset") or [0])[0])

        if max_limit is not None and limit > max_limit:
            limit = max_limit

        return offset, limit, self.get_arguments("expand")

    def paginate_query(self, query, offset, limit):
        total = query.count()

        query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)

        return query, total

    def prepare(self):
        BaseHandler.prepare(self)

        if self.request.method.lower() in ("put", "post"):
            content_type = parse_options_header(
                self.request.headers.get("Content-Type")
            )[0]
            if content_type.lower() != "application/json":
                raise exc.BadRequest("Invalid Content-Type for POST/PUT request.")

        self.add_header(
            "Content-Type",
            "application/json"
        )

        logging.debug(self.request.uri)
        self.href_prefix = "{}://{}{}".format(
            self.request.protocol,
            self.request.host,
            API_VER
        )

        logging.debug("Added headers")

    def not_supported(self):
        self.write({
            "status": "error",
            "error": {
                "code": 405,
                "message": "Method not supported for this resource."
            }
        })
        self.set_status(405, reason="Method not supported.")

    def write_error(self, status_code, **kwargs):

        message = "An unknown problem has occured :("
        if "message" in kwargs:
            message = kwargs['message']

        if "exc_info" in kwargs:
            inst = kwargs["exc_info"][1]
            if isinstance(inst, HTTPError):
                message = inst.log_message
            else:
                message = str(inst)

        self.write({
            "status": "error",
            "error": {
                "code": status_code,
                "message": message,
            },
        })
        self.set_status(status_code, message)

    def success(self, data):
        """200 OK"""
        data['status'] = "ok"
        if 'href' not in data:
            data['href'] = "{}://{}{}".format(
                self.request.protocol,
                self.request.host,
                self.request.uri
            )
        self.write(data)
        self.finish()

    def created(self, location=None, data=None):
        """201 CREATED"""
        self.set_status(201)
        if data is None:
            data = {}
        data['status'] = 'created'
        if location is not None:
            self.set_header(
                "Location",
                urlparse.urljoin(utf8(self.request.uri), utf8(location))
            )
        self.write(data)
        self.finish()
