import datetime
from unittest.mock import patch, MagicMock, call
from pytest import raises
import re

from sqlalchemy.sql import text

from apihandler import APIHandler, ProductAlreadyExists
from .fixtures import session, create_structure, connection, create_offer
from model import Instance, Product, OfferStatus


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


# .list_products() -----------------------------------------------

@patch("requests.post")
def test_list_products(requests_post, session):
    insert_access_token(session)

    handler = APIHandler(session, "URL")
    handler.start("AC_TOKEN")

    requests_post.return_value = MagicMock(
        status_code=201,
        json=MagicMock(return_value={
            "id": 1
        })
    )

    assert handler.create_product("Product 1", "Description") == 1

    requests_post.return_value = MagicMock(
        status_code=201,
        json=MagicMock(return_value={
            "id": 2
        })
    )

    assert handler.create_product("Product 2", "Description") == 2

    result = list(handler.list_products())

    assert result == [
        {
            "id": 1,
            "name": "Product 1",
            "description": "Description",
            "offers": []
        },
        {
            "id": 2,
            "name": "Product 2",
            "description": "Description",
            "offers": []
        },
    ]
    # offers are tested in test_update_offers(...)


# .update_offers() -----------------------------------------------

@patch("requests.post")
@patch("requests.get")
def test_update_offers(requests_get, requests_post, session):
    insert_access_token(session)

    handler = APIHandler(session, "URL")
    handler.start("AC_TOKEN")

    requests_post.return_value = MagicMock(
        status_code=201,
        json=MagicMock(return_value={
            "id": 1
        })
    )

    assert handler.create_product("Product 1", "Description") == 1

    requests_post.return_value = MagicMock(
        status_code=201,
        json=MagicMock(return_value={
            "id": 2
        })
    )

    assert handler.create_product("Product 2", "Description") == 2

    requests_get.side_effect = [
        MagicMock(
            status_code=200,
            json=MagicMock(
                return_value=[
                    {
                        "id": 1,
                        "price": 1000,
                        "items_in_stock": 5,
                    },
                    {
                        "id": 1,
                        "price": 1001,
                        "items_in_stock": 0,
                    },
                    {
                        "id": 1,
                        "price": 1002,
                        "items_in_stock": 7,
                    },
                ]
            )
        ),

        MagicMock(
            status_code=200,
            json=MagicMock(
                return_value=[
                    {
                        "id": 2,
                        "price": 1000,
                        "items_in_stock": 5,
                    },
                ]
            )
        )
    ]

    handler.update_offers()

    requests_get.assert_has_calls([
        call("URL/products/1/offers", data={}, headers={"Bearer": "AC_TOKEN"}),
        call("URL/products/2/offers", data={}, headers={"Bearer": "AC_TOKEN"}),
    ])
    assert list(handler.list_products()) == [
        {
            "id": 1,
            "name": "Product 1",
            "description": "Description",
            "offers": [
                {
                    "price": 1000,
                    "items_in_stock": 5
                },
                {
                    "price": 1002,
                    "items_in_stock": 7
                },
            ]
        },
        {
            "id": 2,
            "name": "Product 2",
            "description": "Description",
            "offers": [
                {
                    "price": 1000,
                    "items_in_stock": 5
                },
            ]
        },
    ]

    requests_get.side_effect = [
        MagicMock(
            status_code=200,
            json=MagicMock(
                return_value=[
                    {
                        "id": 1,
                        "price": 1000,
                        "items_in_stock": 3,
                    },
                    {
                        "id": 1,
                        "price": 1001,
                        "items_in_stock": 2,
                    },
                ]
            )
        ),

        MagicMock(
            status_code=200,
            json=MagicMock(
                return_value=[
                ]
            )
        )
    ]

    handler.update_offers()

    requests_get.assert_has_calls([
        call("URL/products/1/offers", data={}, headers={"Bearer": "AC_TOKEN"}),
        call("URL/products/2/offers", data={}, headers={"Bearer": "AC_TOKEN"}),
    ])
    assert list(handler.list_products()) == [
        {
            "id": 1,
            "name": "Product 1",
            "description": "Description",
            "offers": [
                {
                    "price": 1000,
                    "items_in_stock": 3
                },
                {
                    "price": 1001,
                    "items_in_stock": 2
                },
            ]
        },
        {
            "id": 2,
            "name": "Product 2",
            "description": "Description",
            "offers": []
        },
    ]


# .update_product() -----------------------------------------------


@patch("requests.post")
def test_update_product(requests_post, session):
    insert_access_token(session)

    handler = APIHandler(session, "URL")
    handler.start("AC_TOKEN")

    requests_post.return_value = MagicMock(
        status_code=201,
        json=MagicMock(return_value={
            "id": 1
        })
    )

    assert handler.create_product("Product 1", "Description") == 1
    requests_post.return_value = MagicMock(
        status_code=201,
        json=MagicMock(return_value={
            "id": 2
        })
    )

    assert handler.create_product("Product 2", "Description") == 2

    handler.update_product(1, name="Different name of the same product")

    product = session.query(Product).get(1)

    assert product.name == "Different name of the same product"
    assert product.description == "Description"

    handler.update_product(1, description="Different description")

    product = session.query(Product).get(1)

    assert product.name == "Different name of the same product"
    assert product.description == "Different description"

    with raises(ProductAlreadyExists):
        handler.update_product(1, name="Product 2")


@patch("requests.post")
def test_delete_product(requests_post, session):
    insert_access_token(session)

    handler = APIHandler(session, "URL")
    handler.start("AC_TOKEN")

    requests_post.return_value = MagicMock(
        status_code=201,
        json=MagicMock(return_value={
            "id": 1
        })
    )

    assert handler.create_product("Product 1", "Description") == 1
    requests_post.return_value = MagicMock(
        status_code=201,
        json=MagicMock(return_value={
            "id": 2
        })
    )

    assert handler.create_product("Product 2", "Description") == 2

    handler.delete_product(2)

    products = list(handler.list_products())

    assert len(products) == 1
    assert products[0]["id"] == 1


# .get_price_trend() -----------------------------------------------


def test_get_price_trend(session, connection):
    product = Product(name="Test product", description="Description")

    session.add(product)
    session.commit()
    session.flush()

    session.refresh(product)

    handler = APIHandler(session, "URL")  # no start this time! We don't need communication with API.

    # create test data
    create_offer(session, 1, 1, 1, datetime.datetime(2021, 7, 1, 12, 0, 0), OfferStatus.historic)

    create_offer(session, 1, 1, 0, datetime.datetime(2021, 7, 1, 12, 1, 0), OfferStatus.historic)
    create_offer(session, 1, 2, 2, datetime.datetime(2021, 7, 1, 12, 1, 0), OfferStatus.historic)
    create_offer(session, 1, 3, 3, datetime.datetime(2021, 7, 1, 12, 1, 0), OfferStatus.historic)

    create_offer(session, 1, 1, 0, datetime.datetime(2021, 7, 1, 12, 2, 0), OfferStatus.historic)
    create_offer(session, 1, 2, 0, datetime.datetime(2021, 7, 1, 12, 2, 0), OfferStatus.historic)
    create_offer(session, 1, 3, 3, datetime.datetime(2021, 7, 1, 12, 2, 0), OfferStatus.historic)
    create_offer(session, 1, 4, 4, datetime.datetime(2021, 7, 1, 12, 2, 0), OfferStatus.historic)

    create_offer(session, 1, 4, 4, datetime.datetime(2021, 7, 1, 12, 3, 0), OfferStatus.historic)

    create_offer(session, 1, 5, 5, datetime.datetime(2021, 7, 1, 12, 4, 0), OfferStatus.historic)

    create_offer(session, 1, 6, 6, datetime.datetime(2021, 7, 1, 12, 5, 0), OfferStatus.historic)

    session.commit()

    trend = handler.get_price_trend(
        1,
        start=datetime.datetime(2021, 7, 1, 12, 0, 0),
        end=datetime.datetime(2021, 7, 1, 12, 5, 0)
    )

    assert trend == [
        {
            "price": 1,
            "acquired_on": datetime.datetime(2021, 7, 1, 12, 0, 0)
        },
        {
            "price": 2,
            "acquired_on": datetime.datetime(2021, 7, 1, 12, 1, 0)
        },
        {
            "price": 3,
            "acquired_on": datetime.datetime(2021, 7, 1, 12, 2, 0)
        },
        {
            "price": 4,
            "acquired_on": datetime.datetime(2021, 7, 1, 12, 3, 0)
        },
        {
            "price": 5,
            "acquired_on": datetime.datetime(2021, 7, 1, 12, 4, 0)
        },
        {
            "price": 6,
            "acquired_on": datetime.datetime(2021, 7, 1, 12, 5, 0)
        },
    ]

    trend = handler.get_price_trend(
        1,
        start=datetime.datetime(2021, 7, 1, 12, 2, 0),
        end=datetime.datetime(2021, 7, 1, 12, 3, 0)
    )

    assert trend == [
        {
            "price": 3,
            "acquired_on": datetime.datetime(2021, 7, 1, 12, 2, 0)
        },
        {
            "price": 4,
            "acquired_on": datetime.datetime(2021, 7, 1, 12, 3, 0)
        }
    ]


# .get_history() -----------------------------------------------

def test_get_history(session, connection):
    product = Product(name="Test product", description="Description")
    session.add(product)

    handler = APIHandler(session, "URL")  # no start this time! We don't need communication with API.

    # create test data
    create_offer(session, 1, 1, 1, datetime.datetime(2021, 7, 1, 12, 0, 0), OfferStatus.historic)

    create_offer(session, 1, 3, 1, datetime.datetime(2021, 7, 1, 12, 1, 0), OfferStatus.historic)

    create_offer(session, 1, 2, 1, datetime.datetime(2021, 7, 1, 12, 2, 0), OfferStatus.active)

    session.commit()

    history = handler.get_history(1, datetime.datetime(2021, 7, 1, 12, 0, 0), datetime.datetime(2021, 7, 1, 12, 2, 0))

    assert history == {
        "history": [
            {
                "price": 1,
                "acquired_on": datetime.datetime(2021, 7, 1, 12, 0, 0)
            },
            {
                "price": 3,
                "acquired_on": datetime.datetime(2021, 7, 1, 12, 1, 0)
            },
            {
                "price": 2,
                "acquired_on": datetime.datetime(2021, 7, 1, 12, 2, 0)
            },
        ],
        "rise_or_fall": 100.0
    }

    product = Product(name="Test product 2", description="Description")
    session.add(product)

    # create test data for the second time
    create_offer(session, 2, 10, 1, datetime.datetime(2021, 7, 1, 12, 0, 0), OfferStatus.historic)

    create_offer(session, 2, 5, 1, datetime.datetime(2021, 7, 1, 12, 1, 0), OfferStatus.historic)

    create_offer(session, 2, 2, 1, datetime.datetime(2021, 7, 1, 12, 2, 0), OfferStatus.active)

    session.commit()

    history = handler.get_history(2, datetime.datetime(2021, 7, 1, 12, 0, 0), datetime.datetime(2021, 7, 1, 12, 2, 0))

    assert history == {
        "history": [
            {
                "price": 10,
                "acquired_on": datetime.datetime(2021, 7, 1, 12, 0, 0)
            },
            {
                "price": 5,
                "acquired_on": datetime.datetime(2021, 7, 1, 12, 1, 0)
            },
            {
                "price": 2,
                "acquired_on": datetime.datetime(2021, 7, 1, 12, 2, 0)
            },
        ],
        "rise_or_fall": -80.0
    }

