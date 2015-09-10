import os
import logging

from tornado import web

# Logging object
log = logging.getLogger(__name__)

class NgApp(web.RequestHandler):
    """Our generic handler to serve out the root of our AngularJS app."""
    def get(self):
        self.render(
            os.path.join(os.path.dirname(__file__), "../webapp/build/index.html")
        )
