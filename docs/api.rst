API Documentation
*****************

Hermes is designed as an API first so anything possible in the Web UI
or command line tools would be available here.

Authentication
--------------

Authentication is still in the works.  Right now, Hermes API is expected to sit behind some kind of authenticating proxy.

Requests
--------

In addition to the authentication header above all ``POST``/``PUT`` requests
will be sent as json rather than form data and should include the header ``Content-Type: application/json``


Responses
---------
All responses will be in ``JSON`` format along with the header
``Content-Type: application/json`` set.

The ``JSON`` payload will be in one of two potential structures and will always contain a ``status`` field to distinguish between them. If the ``status`` field
has a value of ``"ok"`` or ``"created"``, then the request (or creation, respectively) was successful and the response will
be available the remaining fields.

.. sourcecode:: javascript

    {
        "status": "ok",
        "id": 1,
        ...
    }

If the ``status`` field has a value of ``"error"`` then the response failed
in some way. You will have access to the error from the ``error`` field which
will contain an error ``code`` and ``message``.

.. sourcecode:: javascript

    {
        "status": "error",
        "error": {
            "code": 404,
            "message": "Resource not found."
        }
    }

Pagination
----------

Most, if not all, responses that return a list of resources will support pagination. If the
``data`` object on the response has a ``total`` attribute then the endpoint supports pagination.
When making a request against this endpoint ``limit`` and ``offset`` query parameters are
supported.

An example response for querying the ``sites`` endpoint might look like:

.. sourcecode:: javascript

    {
        "status": "ok",
        "hosts": [
            {
                "id": 1
                "hostname": "example",
                "href": "/api/v1/hostname/example",
            }
        ],
        "limit": 10,
        "offset": 0,
        "total": 1
    }

