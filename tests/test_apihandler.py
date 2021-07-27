import datetime
from unittest.mock import patch, MagicMock

from apihandler import APIHandler
from fixtures import session, create_structure, connection
from model import Instance


# .start() -----------------------------------------------------------

@patch("requests.post")
def test_new_auth(requests_post, session):
    request = MagicMock(
        status_code=201,
        json=MagicMock(return_value={
            "access_token": "AC_TOKEN"
        })
    )
    requests_post.return_value = request

    handler = APIHandler(session, "URL")
    handler.start()

    requests_post.assert_called_with("URL/auth")
    assert session.query(Instance).first().access_token == "AC_TOKEN"
    assert handler._current_instance_id == 1
    assert handler._current_access_token == "AC_TOKEN"

@patch("requests.post")
def test_already_authenticated(requests_post, session):
    instance = Instance(access_token="AC_TOKEN", date=datetime.datetime.now())

    session.add(instance)
    session.commit()

    handler = APIHandler(session, "AC_TOKEN")
    handler.start("AC_TOKEN")

    requests_post.assert_not_called()
    assert handler._current_instance_id == 1
    assert handler._current_access_token == "AC_TOKEN"
