import enum

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Boolean
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
    active = Column(Boolean, default=True)

    instance_id = Column(Integer, ForeignKey("instance.id"))
    offers = relationship("Offer", lazy="dynamic")


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

    product_id = Column(Integer, ForeignKey("product.id"))
