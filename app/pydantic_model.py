from typing import Optional
import datetime

from pydantic import BaseModel


class Product(BaseModel):
    name: str
    description: str


class UpdateProduct(BaseModel):
    product_id: int
    name: Optional[str]
    description: Optional[str]


class TimeRange(BaseModel):
    start: Optional[datetime.datetime]
    end: Optional[datetime.datetime]
