import enum

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship

from database import Base


class Instance(Base):
    __tablename__ = "instance"
    id = Column(Integer, primary_key=True)
    access_token = Column(String, unique=True)
    date = Column(DateTime, nullable=False)
    products = relationship("Product")


class Product(Base):
    __tablename__ = "product"
    id = Column(Integer, primary_key=True)
    name = Column(String(256), nullable=False, unique=True)
    description = Column(String)

    instance_id = Column(Integer, ForeignKey("instance.id"))


class OfferStatus(enum.Enum):
    active = 0
    historic = 1
    deleted = 2


class Offer(Base):
    __tablename__ = "offer"
    id = Column(Integer, primary_key=True)
    price = Column(Integer, nullable=False)
    items_in_stock = Column(Integer, nullable=False)
    acquired_on = Column(DateTime, nullable=False)
    status = Column(Enum(OfferStatus), nullable=False)
