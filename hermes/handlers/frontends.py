import tornado.web

from hermes.handlers.util import FeHandler


class AppHandler(FeHandler):
    @tornado.web.authenticated
    def get(self):
        return self.render("app.html")
