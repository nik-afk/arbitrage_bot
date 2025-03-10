from cex.mexc_spot_v3 import mexc_market
from decimal import Decimal
from cex.mexc_spot_v3 import MexcAccount
from config.config import api_key, secret_key
from logger.logger_config import logger


trx_quantity = 1

def get_balance_mexc():
    try:
        asset = "USDT"
        account = MexcAccount(api_key, secret_key)
        balances = account.get_balance()
        for asset_item in balances['balances']:
            if asset_item['asset'] == asset:
                free_balance = float(asset_item['free'])
                logger.log("BALANCE",f"Mexc_balance {asset}: {free_balance}")
                return free_balance

        logger.info(f"Баланс на MEXC для {asset} не найден.")
        return 0.0
    except Exception as e:
        logger.error(f"Ошибка при получении баланса на MEXC: {str(e)}")
        return 0.0

def get_balance(asset):
    try:
        account = MexcAccount(api_key, secret_key)
        balances = account.get_balance()
        for asset_item in balances['balances']:
            if asset_item['asset'] == asset:
                return float(asset_item['free'])
        logger.log("BALANCE" ,(f"Баланс для {asset} не найден."))
        return 0.0
    except Exception as e:
        logger.error(f"Ошибка при получении баланса: {str(e)}")
        return 0.0



def get_average_trx_price(trx_received):
    try:
        trade_instance = mexc_market()
        params = {
            "symbol": ""
        }
        avg_price_data = trade_instance.get_avgprice(params)
        avg_price = Decimal(avg_price_data.get("price"))
        trx_received = Decimal(trx_received)
        price_usdt = avg_price * trx_received
        logger.info(f"get_average_trx_price passed succussful: {price_usdt}")
        return price_usdt
    except Exception as e:
        logger.error(f"Ошибка при получении средней цены TRX: {str(e)}")
        return None

