import requests
import math
from cex import mexc_spot_v3
from logger.logger_config import logger
import sys
from decimal import Decimal, ROUND_DOWN

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

def create_market_order(quantity):
    trade = mexc_spot_v3.mexc_trade()
    params = {
        "symbol": '',
        "side": "BUY",
        "type": "MARKET",
        "quantity": str(quantity)
    }
    try:
        response = trade.post_order(params)
        if 'code' in response and response['code'] == 30004:
            logger.error(f"Ошибка создания ордера (недостаточно средств): {response}")
            return None, False
        logger.info(f"Маркет-ордер успешно создан: {response}")
        return response.get('orderId'), True
    except Exception as e:
        logger.error(f"Ошибка при создании ордера: {str(e)}")
        sys.exit(1)

def estimate_tokens_for_usdt(usdt_balance):
    order_book = get_order_book()

    if not order_book or "asks" not in order_book:
        logger.error("Ошибка при получении ордербука для расчета покупки.")
        return Decimal('0')

    total_quantity = Decimal('0')
    remaining_usdt = Decimal(usdt_balance)  # Преобразуем в Decimal

    for ask in order_book['asks']:
        price = Decimal(ask[0])  # Преобразуем в Decimal
        quantity = Decimal(ask[1])  # Преобразуем в Decimal
        cost = price * quantity

        if cost <= remaining_usdt:
            total_quantity += quantity
            remaining_usdt -= cost
        else:
            partial_quantity = remaining_usdt / price
            total_quantity += partial_quantity
            break

    logger.info(f"Можно купить {total_quantity:.6f} токенов за {usdt_balance} USDT.")
    return total_quantity

def execute_market_trade(usdt_balance):
    estimated_tokens = estimate_tokens_for_usdt(Decimal(usdt_balance))  # Убедитесь, что usdt_balance - Decimal

    if estimated_tokens > 0:
        rounded_tokens = estimated_tokens - Decimal('0.01')
        rounded_tokens = rounded_tokens.quantize(Decimal('0.01'), rounding=ROUND_DOWN)
        logger.info(f"Можно купить {rounded_tokens:.2f} токенов за {usdt_balance:.6f} USDT.")
        order_id, success = create_market_order(rounded_tokens)

        if success:
            logger.info(f"Маркет ордер создан: ID {order_id}, количество: {rounded_tokens:.2f}")
            return order_id
        else:
            logger.error("Не удалось создать маркет ордер.")
            sys.exit(1)
    else:
        logger.error("Ошибка при расчете количества токенов для покупки.")
        sys.exit(1)

if __name__ == '__main__':
    usdt_balance = 1.3
    estimate_tokens_for_usdt(usdt_balance)
