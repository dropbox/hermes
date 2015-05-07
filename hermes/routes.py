from .handlers import frontends

HANDLERS = [
    # Frontend Handlers
    (r".*", frontends.AppHandler),
]
