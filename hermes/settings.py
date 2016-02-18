import yaml


class Settings(object):
    def __init__(self, initial_settings):
        self.settings = initial_settings

    @classmethod
    def from_settings(cls, settings, initial_settings=None):
        _settings = {}
        _settings.update(settings.settings)
        if initial_settings:
            _settings.update(initial_settings)
        return cls(_settings)

    def update_from_config(self, filename):
        with open(filename) as config:
            data = yaml.safe_load(config.read())

        settings = {}
        settings.update(data)

        for key, value in settings.iteritems():
            key = key.lower()

            if key not in self.settings:
                continue

            override = getattr(self, "override_%s" % key, None)
            if override is not None and callable(override):
                value = override(value)

            self.settings[key] = value

    def __getitem__(self, key):
        return self.settings[key]

    def __getattr__(self, name):
        try:
            return self.settings[name]
        except KeyError as err:
            raise AttributeError(err)


settings = Settings({
    "log_format": "%(asctime)-15s\t%(levelname)s\t%(message)s",
    "num_processes": 1,
    "database": None,
    "query_server": "http://localhost:5353/api/query",
    "frontend": "https://hermes.company.net",
    "slack_webhook": None,
    "slack_proxyhost": None,
    "debug": False,
    "domain": "localhost",
    "port": 8990,
    "user_auth_header": "X-Hermes-Email",
    "email_notifications": False,
    "email_sender_address": "hermes@localhost",
    "email_always_copy": "",
    "restrict_networks": [],
    "bind_address": None,
    "api_xsrf_enabled": True,
    "secret_key": "SECRET_KEY",
    "auth_token_expiry": 600,  # 10 minutes
    "sentry_dsn": None,
    "plugin_dir": "plugins ",
    "environment": "dev",
    "dev_email_recipient": "",
    "fullstory_id": None,
    "strongpoc_server": None,
})
