import time
import sys
from Transaction.swap import balance_token, main_swap, truncate
from serch.bot import compare_prices
from logger.logger_config import logger
from cex.test_order import execute_market_trade
from cex.orders import get_balance_mexc, get_average_trx_price
from decimal import Decimal
from serch.bot import difference
from cex.mexc_spot_v3 import mexc_trade

buying_price = 0
selling_price = 0
swap_fee = 0

def check_balance():
    logger.info("Проверка баланса на DEX и CEX...")
    token_balance = balance_token()
    usdt_balance = get_balance_mexc()

    if token_balance == 0:
        logger.error("Недостаточно токенов для продажи на DEX. Операция прервана.")
        return False

    # if usdt_balance < Decimal("5"):
    #     logger.error("Недостаточно USDT на CEX. Операция прервана.")
    #     return False

    return True

def main_launch():
    if not check_balance():
        logger.error("Проверка баланса не пройдена. Убедитесь, что на DEX есть токены, а на CEX — USDT.")
        time.sleep(3)

    logger.info("Поиск арбитражных возможностей.")

    while True:
        try:
            result = compare_prices()
        except Exception as e:
            logger.error(f"Ошибка в compare_prices: {str(e)}")
            time.sleep(1)
            continue

        amount_to_sell = 2160

        if result:
            profit, dex_price, limit_price, cex_buy_price = result
            profit_t = truncate(Decimal(profit), 2)

            logger.log("PROFIT",
                       f"Current Profit: {profit_t}, Dex Price: {dex_price}, Limit price: {limit_price}, CEX Sell Price: {cex_buy_price}")

            if profit_t > 0.8:
                logger.info(f"Прибыль достаточна ({profit_t}). Начинаем продажу на DEX и покупку на CEX.")
                swap_success = execute_dex_sale(limit_price, amount_to_sell)

                if swap_success:
                    logger.info("Swap successful. Starting post-swap operations.")
                    order_id = execute_cex_purchase(swap_success)
                    calculate_and_log_profit(order_id, amount_to_sell)
                    break
                else:
                    logger.info("Продажа на DEX не выполнена, продолжаем поиск профита.")
            else:
                logger.info(f"Прибыль недостаточна ({profit_t}). Ожидание лучшей возможности.")

        time.sleep(1)

def execute_dex_sale(limit_price, amount_to_sell):
    global selling_price, swap_fee
    try:
        trx_received, dex_fee, sale_price = main_swap(limit_price, amount_to_sell)
        swap_fee = dex_fee
        price_adjusted = sale_price * Decimal("1.003")
        diff = difference()
        selling_price_avant = price_adjusted * diff
        selling_price = truncate(selling_price_avant, 6)
        return trx_received if trx_received is not None else None
    except Exception as e:
        logger.error(f"Ошибка при продаже на DEX: {str(e)}")
        return None

def execute_cex_purchase(trx_received):
    try:
        amount_usdt_to_buy = get_average_trx_price(trx_received)
        order_id = execute_market_trade(amount_usdt_to_buy)
        return order_id
    except Exception as e:
        logger.error(f"Ошибка при покупке на CEX: {str(e)}")
        sys.exit(1)

def calculate_and_log_profit(order_id, amount_to_change):
    global swap_fee, transfer_fee, buying_price, selling_price
    trade_instance = mexc_trade()
    params = {
        "symbol": ""
    }
    trades = trade_instance.get_mytrades(params)
    order_id_to_check = order_id
    trade = next((t for t in trades if t["orderId"] == order_id_to_check), None)
    buying_price = trade['price']

    qty = trade['qty']
    commission_usdt = trade['commission']

    logger.log("SUMMARY",f"----- ARBITRAGE SUMMARY -----")
    logger.log("SUMMARY",f"Selling Price (DEX): {selling_price}")
    logger.log("SUMMARY",f"Buying Price  (CEX): {buying_price}")
    logger.log("SUMMARY",f"Swap Fee_TRX: {swap_fee}")
    logger.log("SUMMARY",f"Commission_USDT: {commission_usdt}")
    logger.log("SUMMARY",f"token qty_sell: {amount_to_change}")
    logger.log("SUMMARY",f"token qty_buy: {qty}")
    logger.log("SUMMARY",f"--------------------------------")

if __name__ == '__main__':
    main_launch()
