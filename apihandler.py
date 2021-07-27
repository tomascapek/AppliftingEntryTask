from typing import Optional
import datetime

import requests
from sqlalchemy.orm import session

from model import Instance, Product


class ProductAlreadyExists(RuntimeError):
    pass


class APIHandler:
    _base_url: str  # without trailing /
    _session: session  # database session

    _current_access_token: Optional[str] = None
    _current_instance_id: Optional[int] = None

    def _check_auth(self):
        if self._current_instance_id is None or self._current_access_token is None:
            raise RuntimeError("Instance ID or access token are not set in this instance! Call start(..) first!")

    def __init__(self, db_session: session, base_url: str):
        self._session = db_session
        self._base_url = base_url

    def start(self, access_token: Optional[str] = None):
        if access_token is None:
            request = requests.post(self._base_url + "/auth")

            if request.status_code == 201:
                data = request.json()

                instance = Instance(
                    access_token=data["access_token"],
                    date=datetime.datetime.now()
                )

                self._session.add(instance)
                self._session.flush()
                self._session.commit()

                self._session.refresh(instance)

                self._current_access_token = data["access_token"]
                self._current_instance_id = instance.id
            else:
                raise RuntimeError(f"/auth returned {request.status_code}, which is not 201. Cannot continue.")
        else:
            instance = self._session.query(Instance).filter(Instance.access_token == access_token).first()

            if instance is None:
                raise RuntimeError("Invalid access token given.")
            else:
                self._current_access_token = access_token
                self._current_instance_id = instance.id

    def create_product(self, name: str, description: str) -> int:
        self._check_auth()

        product = Product(name=name, description=description, instance_id=self._current_instance_id)

        query = self._session.query(Product).filter(Product.name == name).first()

        if query is not None:
            raise ProductAlreadyExists()

        self._session.add(product)
        self._session.flush()
        self._session.commit()

        self._session.refresh(product)

        request = requests.post(
            self._base_url + "/products/register",
            data={
                "id": product.id,
                "name": name,
                "description": description
            },
            headers={
                "Bearer": self._current_access_token
            }
        )

        if request.status_code == 201:
            return product.id
        else:
            self._session.query(Product).filter(Product.id == product.id).delete()
            self._session.commit()

            if request.status_code == 400:
                raise RuntimeError("Returned 400 BAD REQUEST. Cannot continue.")
            elif request.status_code == 401:
                raise RuntimeError("Returned 401 UNAUTHORIZED. Cannot continue.")

    def list_products(self):
        return self._session.query(Product).all()

    def update_product(self, product_id: int, name: Optional[str] = None, description: Optional[str] = None):
        pass

    def delete_product(self, product_id: int):
        pass

    def update_offers(self):
        pass


