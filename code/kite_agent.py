import logging
from kiteconnect import KiteConnect

logging.basicConfig(level=logging.DEBUG)

class KiteAgent:
    kite = None
    def __init__(self):
        self.kite = KiteConnect(api_key="z102ygbcfqtv6jfw")
        self.kite.set_access_token("Kq07pZrV277nXC7JrfDe2j60eyAlZ4sN")


    def login(self):
        url = self.kite.login_url()
        print(url)
        # Redirect the user to the login url obtained
        # from kite.login_url(), and receive the request_token
        # from the registered redirect url after the login flow.
        # Once you have the request_token, obtain the access_token
        # as follows.

        data = self.kite.generate_session("FtfiSYOv8b1ICJrEcX0Ura5B7UdFBt3L", api_secret="cib9xpae769cbip683e7bmcs4t5sn12k")
        self.kite.set_access_token(data["access_token"])
        print(data["access_token"])

    def place_order(self):
        # Place an order
        try:
            order_id = self.kite.place_order(tradingsymbol="INFY",
                                        exchange=self.kite.EXCHANGE_NSE,
                                        transaction_type=self.kite.TRANSACTION_TYPE_BUY,
                                        quantity=1,
                                        variety=self.kite.VARIETY_AMO,
                                        order_type=self.kite.ORDER_TYPE_MARKET,
                                        product=self.kite.PRODUCT_CNC,
                                        validity=self.kite.VALIDITY_DAY)

            logging.info("Order placed. ID is: {}".format(order_id))
        except Exception as e:
            logging.info("Order placement failed: {}".format(e.message))


    def fetch_orders(self):
        # Fetch all orders
        orders = self.kite.orders()
        return orders

    def fetch_instruments(self):
        # Get instruments
        instruments = self.kite.instruments()
        return instruments

agent = KiteAgent()
# agent.login()
# agent.place_order()
print(agent.fetch_orders())
# print(agent.fetch_instruments())
