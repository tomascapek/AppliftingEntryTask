import datetime

import pytest
from sqlalchemy.orm import sessionmaker, session
from sqlalchemy import create_engine

import model

Session = sessionmaker()

@pytest.fixture(scope="session")
def connection():
    engine = create_engine('sqlite:///test-database.db')
    yield engine.connect()
    # connection.close() # removed, because SQLite


@pytest.fixture(scope="session")
def create_structure(connection):
    model.Base.metadata.bind = connection
    model.Base.metadata.create_all()
    yield
    model.Base.metadata.drop_all()


@pytest.fixture(scope='function')
def session(create_structure, connection):
    transaction = connection.begin()
    session = Session(bind=connection)
    yield session
    session.close()
    transaction.rollback()

def create_offer(
    session: session,
    product_id: int,
    price: int,
    stock: int,
    date: datetime.datetime,
    status: model.OfferStatus
):
    offer = model.Offer(
        product_id=product_id,
        price=price,
        items_in_stock=stock,
        acquired_on=date,
        status=status
    )
    session.add(offer)