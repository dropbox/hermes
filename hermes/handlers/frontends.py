import tornado.web

from hermes.handlers.util import FeHandler


class AppHandler(FeHandler):
    def get(self):
        return self.render("app.html")
