from .handlers import frontends, api

HANDLERS = [
    # Hosts
    (r"/api/v1/hosts", api.HostsHandler),
    (r"/api/v1/hosts/(?P<hostname>.*)", api.HostHandler),

    # Frontend Handlers
    (r"/.*", frontends.AppHandler),
]
