from typing import Optional, Dict, List, Any
import datetime

import requests
from sqlalchemy.orm import session

from model import Instance, Product, Offer, OfferStatus


class NotAuthenticated(RuntimeError):
    pass


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

    def _check_auth(self) -> bool:
        """
        Checks, whether we are authenticated and ready to send requests to given API.

        :returns True if you can safely send requests, False otherwise
        """
        if self._current_instance_id is None or self._current_access_token is None:
            raise NotAuthenticated()

    def __init__(self, db_session: session, base_url: str) -> None:
        self._session = db_session
        self._base_url = base_url

    def start(self, access_token: Optional[str] = None) -> None:
        """
        Does authentication handshake, if None is given as access_token. In both cases,
        setups inner structures before communication with API.

        :param access_token: is valid access token or None, if you want to get one and save it to database

        :raises RuntimeError: if not 201 is returned from API.
        """
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
        """
        Create new product and register it with the API.

        :param name: unique name for product
        :param description: description of the product

        :raises RuntimeError: if 4xx is returned from API.
        :raises ProductAlreadyExists: if product with the same name is already registered
        :raises NotAuthenticated: if you failed to call .start() in before.

        :return: ID of new product or exception, if it fails.
        """
        self._check_auth()

        product = Product(name=name, description=description, instance_id=self._current_instance_id)

        query = self._session.query(Product).filter(Product.name == name).first()

        # I was not sure, whether we want the same ID for previously existing product or not,
        # but I decided, that it makes sense to do so
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

    def list_products(self) -> List[Dict[str, Any]]:
        """
        List all products with all offers, that has some products in stock.

        :return: Dict with data.
        """
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

    def update_product(self, product_id: int, name: Optional[str] = None, description: Optional[str] = None) -> None:
        """
        Change product properties.

        :param product_id: ID of product, on which we will do given changes.
        :param name: None, if you don't want to change name or new name.
        :param description: None, if you don't want to change description or new description.

        :raises ProductAlreadyExists: if new name is already in database.
        :raises ProductDoesntExists: if given ID isn't present in database.
        """

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

    def delete_product(self, product_id: int) -> None:
        """
        Delete product from database.

        :param product_id: ID of product to be deleted

        :raises ProductDoesntExist: if product ID doesn't exist in the database.
        """
        product = self._session.query(Product).get(product_id)

        if product is None or not product.active:
            raise ProductDoesntExist(product_id)

        product.active = False

        self._session.query(Offer).filter(Offer.product_id == product_id, Offer.status == OfferStatus.active).update({
            "status": OfferStatus.historic
        })

        self._session.commit()

    def update_offers(self) -> None:
        """
        Get updated offers from API.

        :raises NotAutheticated: If you failed to call .start() in before this.
        :raises RuntimeError: If non 200 response is received.
        """
        self._check_auth()

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

                got_new_offers: bool = False

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

    def get_price_trend(self, product_id: int, start: Optional[datetime.datetime] = None, end: Optional[datetime.datetime] = None):
        """
        Returns sorted list with history of offer price for given product.

        If start is None, it will assume, you want last 5 minutes.

        :raises: ProductDoesntExists: if Product doesnt exist

        :param product_id: of desired product
        :param start: starting time or None
        :param end: ending time or None
        :return: list of offer history
        """
        product = self._session.query(Product).get(product_id)

        if product is None or not product.active:
            raise ProductDoesntExist(product_id)

        if start is None:
            now = datetime.datetime.now()
            start = now - datetime.timedelta(minutes=5)
            end = now
        else:
            if start > end:
                buffer = end
                end = start
                start = buffer

        offers = self._session.query(Offer).filter(Offer.product_id == product_id, Offer.acquired_on >= start, Offer.acquired_on <= end)

        best_offers = dict()
        for offer in offers.all():
            if offer.items_in_stock == 0:
                continue

            if str(offer.acquired_on) not in best_offers:
                best_offers[str(offer.acquired_on)] = offer.price
            else:
                if best_offers[str(offer.acquired_on)] > offer.price:
                    best_offers[str(offer.acquired_on)] = offer.price

        grouped_offers = self._session.query(Offer).filter(Offer.acquired_on >= start, Offer.acquired_on <= end).group_by(Offer.acquired_on)

        result = list()
        for offer in grouped_offers.all():
            if str(offer.acquired_on) in best_offers:
                result.append({
                    "price": best_offers[str(offer.acquired_on)],
                    "acquired_on": offer.acquired_on
                })

        return result

    def get_history(self, product_id: int, start: Optional[datetime.datetime] = None, end: Optional[datetime.datetime] = None):
        """
        Get history of offers for given products and calculate rise or fall of the price.

        :raises: ProductDoesntExists: if Product doesnt exist

        :param product_id: of desired product
        :param start: start time or None
        :param end: end time or None
        :return: History, with calculated rise or fall.
        """
        product = self._session.query(Product).get(product_id)

        if product is None or not product.active:
            raise ProductDoesntExist(product_id)

        history = self.get_price_trend(product_id, start, end)

        if len(history) == 0:
            return []
        elif len(history) == 1:
            return {
                "history": history,
                "rise_or_fall": 0.0
            }
        else:
            return {
                "history": history,
                "rise_or_fall": (history[-1]["price"] - history[0]["price"])/(history[0]["price"]/100.0)
            }
