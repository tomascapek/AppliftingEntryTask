from typing import Optional
import datetime
import json

import requests
from sqlalchemy.orm import session

from model import Instance

class APIHandler:
    _base_url: str # without trailing /
    _session: session # database session

    _current_access_token: str

    def __init__(self, session: session, base_url: str):
        self._session = session
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
                self._session.commit()

                self._current_access_token = data["access_token"]
            else:
                raise RuntimeError(f"/auth returned {request.status_code}, which is not 201. Cannot continue.")
        else:
            instance = self._session.query(Instance).filter(Instance.access_token==access_token).first()

            if instance is None:
                raise RuntimeError("Invalid access token given.")
            else:
                self._current_access_token = access_token

    def create_product(self, name: str, description: str) -> int:
        pass

    def read_product(self, product_id: int):
        pass

    def update_product(self, product_id: int, name: Optional[str] = None, description: Optional[str] = None):
        pass

    def delete_product(self, product_id: int):
        pass

    def update_offers(self):
        pass

    def list_products(self):
        pass
