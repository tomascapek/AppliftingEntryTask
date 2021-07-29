from typing import Optional
import datetime

import requests
from sqlalchemy.orm import session

from model import Instance, Product, Offer, OfferStatus


class ProductAlreadyExists(RuntimeError):
    pass



class ProductDoesntExist(RuntimeError):
    product_id: int

    def __init__(self, product_id: int):
        super().__init__(f"Product with id {product_id} doesn't exist!")


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

        # TODO: this is possibly not what we want - maybe we want a new ID for existing deleted Product
        if query is not None:
            if not query.active:
                query.active = True

                self._session.commit()

                product = query
            else:    
                raise ProductAlreadyExists()
        else:
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
        for product in self._session.query(Product).filter(Product.active == True).all():
            data = {
                "id": product.id,
                "name": product.name,
                "description": product.description,
                "offers": []
            }

            for offer in product.offers.filter(Offer.status == OfferStatus.active):
                if offer.items_in_stock > 0:
                    data["offers"].append({
                        "price": offer.price,
                        "items_in_stock": offer.items_in_stock,
                    })

            yield data

    def update_product(self, product_id: int, name: Optional[str] = None, description: Optional[str] = None):
        product = self._session.query(Product).get(product_id)

        if product is None:
            raise ProductDoesntExist(product_id)

        query = self._session.query(Product).filter(Product.name == name).first()

        if query is not None:
            raise ProductAlreadyExists()

        if name is not None:
            product.name = name

        if description is not None:
            product.description = description

        self._session.commit()

    def delete_product(self, product_id: int):
        pass

    def update_offers(self):
        products = self._session.query(Product).where(Product.active == True).all()

        for product in products:
            # used in case, when there are no active offers, so that we know, that price was refreshed
            # at the given point - not sure, if necessary, but given API wasn't documented in this regards, so let's
            # play it safe
            best_price_obj = product.offers.filter(Offer.status == OfferStatus.active).order_by(Offer.price).first()

            best_price: int = 0
            if best_price_obj is not None:
                best_price = best_price_obj.price

            active_offers = product.offers.filter(Offer.status == OfferStatus.active)

            active_offers.update({"status": OfferStatus.historic})

            request = requests.get(
                self._base_url + f"/products/{product.id}/offers",
                data={},
                headers={
                    "Bearer": self._current_access_token
                }
            )

            if request.status_code == 200:
                response_data = request.json()

                acquired_on = datetime.datetime.now()

                got_new_offers: Boolean = False

                for offer_data in response_data:
                    got_new_offers = True

                    offer = Offer(
                        price=offer_data["price"],
                        items_in_stock=offer_data["items_in_stock"],
                        acquired_on=acquired_on,
                        status=OfferStatus.active,
                        product_id=product.id
                    )

                    self._session.add(offer)

                if not got_new_offers:
                    offer = Offer(
                        price=best_price,
                        items_in_stock=0,
                        acquired_on=acquired_on,
                        status=OfferStatus.active,
                        product_id=product.id
                    )

                    self._session.add(offer)

                self._session.commit()
            else:
                raise RuntimeError(f"Got {request.status_code} instead od 200.")
