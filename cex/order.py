import requests
import time
import math
from cex import mexc_spot_v3
from logger.logger_config import logger

usdt_balance = 1
sell_price = 1

def play_penny_game(usdt_balance, sell_price):
    def truncate(number, decimals=6):
        factor = 10.0 ** decimals
        return math.floor(number * factor) / factor

    def get_order_book():
        url = "https://api.mexc.com/api/v3/depth"
        params = {
            "symbol": "",
            "limit": 10
        }
        try:
            response = requests.get(url, params=params)
            order_book = response.json()
            return order_book
        except Exception as e:
            logger.error(f"Ошибка при получении книги ордеров: {str(e)}")
            return None

    def create_order(price, quantity):
        trade = mexc_spot_v3.mexc_trade()
        params = {
            "symbol": '',
            "side": "BUY",
            "type": "LIMIT",
            "quantity": str(quantity),
            "price": str(price)
        }
        try:
            response = trade.post_order(params)
            if 'code' in response and response['code'] == 30004:
                logger.error(f"Ошибка создания ордера (Insufficient position): {response}")
                return None, False
            logger.info(f"Ордер создан по цене {price}: {response}")
            return response.get('orderId'), True
        except Exception as e:
            logger.error(f"Ошибка при создании ордера: {str(e)}")
            return None, False

    def cancel_order(order_id):
        trade = mexc_spot_v3.mexc_trade()
        params = {
            "symbol": "",
            "orderId": order_id
        }
        try:
            response = trade.delete_order(params)
            logger.info(f"Ордер {order_id} отменен.")
        except Exception as e:
            logger.error(f"Ошибка при отмене ордера {order_id}: {str(e)}")

    def calculate_profit_percentage(buy_price, sell_price):
        profit_percent = ((sell_price - buy_price) / buy_price) * 100
        return profit_percent

    current_order_id = None
    last_order_price = None
    initial_buy_price = None

    while True:
        order_book = get_order_book()

        if order_book and "bids" in order_book:
            bids = order_book['bids']

            highest_bid_price = max(float(bid[0]) for bid in bids[:10])
            logger.info(f"Наибольшая цена из первых 10 ордеров: {highest_bid_price}")

            price_to_place = None
            for bid in bids:
                bid_price = float(bid[0])
                bid_quantity = float(bid[1])
                if bid_quantity >= 1500:
                    logger.info(f"Найдена цена для ордера > 1500 по объему: {bid_price}")
                    price_to_place = bid_price
                    break

            if price_to_place is None:
                logger.error("Не найдено ордеров с объемом > 1500.")
                continue

            price_to_place = truncate(price_to_place + 0.000001, 6)
            logger.info(f"Цена для размещения ордера после перебивания: {price_to_place}")

            for i, bid in enumerate(bids):
                current_bid_price = float(bid[0])
                if current_bid_price == last_order_price:
                    logger.info(f"Найден мой ордер по цене: {current_bid_price}")

                    if i > 0:
                        previous_bid_price = float(bids[i-1][0])
                        previous_bid_quantity = float(bids[i-1][1])
                        price_diff = current_bid_price - previous_bid_price

                        if previous_bid_quantity >= 1000 and price_diff > 0.000010:

                            price_to_place = truncate(previous_bid_price + 0.000001, 6)
                            logger.info(f"Перебиваем цену на {price_to_place}, так как предыдущий ордер был с объёмом > 1000 и разницей > 0.000010")
                            break

            if price_to_place == last_order_price:
                logger.info(f"Цена для нового ордера ({price_to_place}) совпадает с последней выставленной ценой. Новый ордер не создается.")
                time.sleep(1)
                continue

            if initial_buy_price:
                profit_percent = calculate_profit_percentage(initial_buy_price, price_to_place)
                logger.info(f"Процент прибыли перед выставлением нового ордера: {profit_percent:.2f}%")

            if current_order_id:
                cancel_order(current_order_id)

            quantity_to_buy = truncate((usdt_balance / price_to_place) - 0.2, 2)

            current_order_id, success = create_order(price_to_place, quantity_to_buy)
            if not success:
                logger.error("Процесс торговли остановлен из-за ошибки недостатка средств.")
                break

            last_order_price = price_to_place

        time.sleep(1)

if __name__ == '__main__':
    play_penny_game(usdt_balance, sell_price)
