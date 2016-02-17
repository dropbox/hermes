from .handlers import frontends, api
from tornado import web
import os

HANDLERS = [
    # Hosts
    (r"/api/v1/hosts\/?", api.HostsHandler),
    (r"/api/v1/hosts/(?P<hostname>.*)\/?", api.HostHandler),

    # Event Types
    (r"/api/v1/eventtypes\/?", api.EventTypesHandler),
    (r"/api/v1/eventtypes/(?P<id>\d+)\/?", api.EventTypeHandler),

    # Events
    (r"/api/v1/events\/?", api.EventsHandler),
    (r"/api/v1/events/(?P<id>\d+)\/?", api.EventHandler),

    # Fates
    (r"/api/v1/fates\/?", api.FatesHandler),
    (r"/api/v1/fates/(?P<id>\d+)\/?", api.FateHandler),

    # Labors
    (r"/api/v1/labors\/?", api.LaborsHandler),
    (r"/api/v1/labors/(?P<id>\d+)\/?", api.LaborHandler),

    # Quests
    (r"/api/v1/quests\/?", api.QuestsHandler),
    (r"/api/v1/quests/(?P<id>\d+)\/?", api.QuestHandler),
    (r"/api/v1/quests/(?P<id>\d+)/mail\/?", api.QuestMailHandler),

    # Queries to 3rd party tools
    (r"/api/v1/extquery\/?", api.ExtQueryHandler),

    # Query for the current user
    (r"/api/v1/currentUser", api.CurrentUserHandler),

    # Query the server for its configs
    (r"/api/v1/serverConfig", api.ServerConfig),

    # Frontend Handlers
    (
        r"/((?:css|fonts|img|js|vendor|templates)/.*)",
        web.StaticFileHandler,
        dict(
            path=os.path.join(os.path.dirname(__file__), "webapp/build")
        )
    ),

    # Frontend Handlers
    (
        r"/.*",
        frontends.NgApp
    )
]
