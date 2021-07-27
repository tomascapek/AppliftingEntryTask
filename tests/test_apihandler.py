import datetime
from unittest.mock import patch, MagicMock
from pytest import raises

from apihandler import APIHandler, ProductAlreadyExists
from fixtures import session, create_structure, connection
from model import Instance, Product


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


def insert_access_token(session):
    instance = Instance(access_token="AC_TOKEN", date=datetime.datetime.now())

    session.add(instance)
    session.commit()


@patch("requests.post")
def test_already_authenticated(requests_post, session):
    insert_access_token(session)

    handler = APIHandler(session, "AC_TOKEN")
    handler.start("AC_TOKEN")

    requests_post.assert_not_called()
    assert handler._current_instance_id == 1
    assert handler._current_access_token == "AC_TOKEN"


# .create_product() -----------------------------------------------

@patch("requests.post")
def test_create_new_product(requests_post, session):
    insert_access_token(session)

    product_name = "Product"
    product_description = "Description"

    handler = APIHandler(session, "URL")
    handler.start("AC_TOKEN")

    requests_post.return_value = MagicMock(
        status_code=201,
        json={
            "id": 1
        }
    )

    assert handler.create_product(product_name, product_description) == 1
    requests_post.assert_called_with(
        "URL/products/register",
        data={
            "id": 1,
            "name": product_name,
            "description": product_description
        },
        headers={
            "Bearer": "AC_TOKEN"
        }
    )
    product = session.query(Product).first()
    assert product.id == 1
    assert product.name == product_name
    assert product.description == product_description


@patch("requests.post")
def test_create_existing_product(requests_post, session):
    insert_access_token(session)

    product_name = "Product"
    product_description = "Description"

    handler = APIHandler(session, "URL")
    handler.start("AC_TOKEN")

    product = Product(name=product_name, description=product_description)
    session.add(product)
    session.commit()

    with raises(ProductAlreadyExists):
        handler.create_product(name=product_name, description=product_description)


@patch("requests.post")
def test_create_product_bad_request(requests_post, session):
    insert_access_token(session)

    product_name = "Product"
    product_description = "Description"

    handler = APIHandler(session, "URL")
    handler.start("AC_TOKEN")

    requests_post.return_value = MagicMock(
        status_code=400,
        json={
            "code": "BAD_REQUEST",
            "msg": "Sorry, something went wrong."
        }
    )

    with raises(RuntimeError):
        handler.create_product(product_name, product_description)

    assert session.query(Product).all() == []
