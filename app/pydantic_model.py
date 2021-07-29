from typing import Optional

from pydantic import BaseModel


class Product(BaseModel):
    name: str
    description: str


class UpdateProduct(BaseModel):
    product_id: int
    name: Optional[str]
    description: Optional[str]
