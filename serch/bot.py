import requests
import time
from datetime import datetime
import logger
from logger.logger_config import logger
from tronpy import Tron
from tronpy.keys import PrivateKey
from tronpy.providers import HTTPProvider
from config.config import API_KEY, TOKEN_ADDRESS, SUNSWAP_ADDRESS
import json
from decimal import Decimal, ROUND_DOWN

with open('../Transaction/token.json', 'r') as file:
    TOKEN_ABI = json.load(file)

def truncate(number, digits):
    factor = Decimal('10') ** digits
    return (Decimal(number) * factor).quantize(Decimal('1'), rounding=ROUND_DOWN) / factor

def send_telegram_message(message):
    bot_token = ''
    chat_id = ''
    url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
    payload = {
        'chat_id': chat_id,
        'text': message
    }
    try:
        requests.post(url, data=payload)
    except Exception as e:
        logger.log("PROFIT_ERROR",f"Ошибка отправки сообщения в Telegram: {e}")

def get_cex_sell_price():
    base_url = 'https://api.mexc.com/api/v3/depth'
    params = {
        'symbol': '',
        'limit': 5
    }
    try:
        response = requests.get(base_url, params=params)
        if response.status_code == 200:
            data = response.json()
            asks = data['asks']

            for order in asks:
                price = float(order[0])
                volume = float(order[1])

                if volume > 3000:
                    return price

            logger.log("PROFIT_ERROR", "Нет ордеров с объемом больше 1000.")
            return None
        else:
            logger.log("PROFIT_ERROR", f"Ошибка получения данных с MEXC: {response.status_code}")
            return None
    except Exception as e:
        logger.log("PROFIT_ERROR", f"Произошла ошибка при запросе к API MEXC: {e}")
        return None

def get_wallet_address(private_key: str) -> str:
    return PrivateKey(bytes.fromhex(private_key)).public_key.to_base58check_address()

def query_price(tron: Tron, token_path: list) -> Decimal:
    contract = tron.get_contract(SUNSWAP_ADDRESS)
    contract_token = tron.get_contract(token_path[0])
    contract_token.abi = TOKEN_ABI
    decimals = contract_token.functions.decimals()
    amount = contract.functions.getAmountsOut(1 * 10 ** decimals, token_path)
    amount_in = Decimal(amount[0]) / (10 ** decimals)
    amount_out = Decimal(amount[1]) / (10 ** 6)
    return amount_out / amount_in

def test_price():
    token_path = [TOKEN_ADDRESS, ""]
    tron = Tron(HTTPProvider(timeout=30, api_key=API_KEY))
    price = query_price(tron, token_path)
    price1 = price * (Decimal(1) + (Decimal(0.3) / Decimal(100)))
    price_trx = truncate(price1, 5)
    return price_trx

def check_price():
    url = "https://www.dextools.io/shared/data/pair?address=URL_TOKEN&chain=tron&audit=false&locks=true"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36",
        "Referer": "https://www.dextools.io/",
        "Accept": "application/json"
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        price = data['data'][0]['price']
        price_t = truncate(price, 6)
        return price_t
    else:
        print("Error fetching price data")
        return None

def compare_prices():
    while True:
        cex_sell_price = get_cex_sell_price()
        dex_price_usdt = check_price()
        dex_price_wtrx = test_price()

        if cex_sell_price is None:
            logger.log("PROFIT_ERROR", "Ошибка получения цен с CEX. Повторяем попытку...")
            time.sleep(5)
            continue

        difference = ((dex_price_usdt - Decimal(cex_sell_price)) / Decimal(cex_sell_price)) * 100
        profit = truncate(difference, 3)
        current_time = datetime.now().strftime("%d %H:%M:%S")
        message = (
            f"{current_time}\n"
            f"Profit: {profit:.2f}%\n"
            f"Dex price: {dex_price_usdt}\n"
            f"Cex price (Sell): {cex_sell_price}\n"
            f"dex price wtrx: {dex_price_wtrx}\n"
        )

        # send_telegram_message(message)
        # logger.log("PROFIT", f"Выгодное соотношение найдено: {message}")

        # Отправьте сообщение только если прибыль положительная
        if profit > 2:
            send_telegram_message(message)

        return profit, dex_price_usdt, dex_price_wtrx, cex_sell_price
        # print(profit, dex_price_usdt, dex_price_wtrx, cex_sell_price)
        # diff = dex_price_usdt / dex_price_wtrx
        # print(diff)
        # r = 0.03668
        # r_2 = Decimal(r) * diff
        # r_2 = truncate(r_2,6)
        # print(r_2)
        time.sleep(1)

def difference():
    price_t = check_price()
    price_trx = test_price()
    diff = price_t/ price_trx
    # print(diff)
    return diff



if __name__ == "__main__":
        # while True:
        #     compare_prices()
        price_trx = test_price()
        price_t = check_price()
        difference(price_t,price_trx)