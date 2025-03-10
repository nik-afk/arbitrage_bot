from datetime import datetime, timedelta
import logger
from logger.logger_config import logger
from tronpy import Tron
from tronpy.keys import PrivateKey
from tronpy.providers import HTTPProvider
from config.config import API_KEY, TOKEN_ADDRESS, PRIVATE_KEY, SLIPPAGE, SUNSWAP_ADDRESS
import json
import sys
from decimal import Decimal, ROUND_DOWN

with open('../Transaction/token.json', 'r') as file:
    TOKEN_ABI = json.load(file)

def get_wallet_address(private_key: str) -> str:
    return PrivateKey(bytes.fromhex(private_key)).public_key.to_base58check_address()

def truncate(number, decimals=3):
    factor = Decimal(10) ** -decimals
    return number.quantize(factor, rounding=ROUND_DOWN)

def erc20_balance(tron: Tron, wallet: str, contract_address: str) -> Decimal:
    contract = tron.get_contract(contract_address)
    contract.abi = TOKEN_ABI
    balance = contract.functions.balanceOf(wallet)
    decimals = contract.functions.decimals()
    return Decimal(balance) / (10 ** decimals)

def approve_erc20_to_sunswap(tron: Tron, wallet: str, private_key: str, contract_address: str):
    contract = tron.get_contract(contract_address)
    contract.abi = TOKEN_ABI
    approve_amount = 2 ** 256 - 1
    amount = contract.functions.allowance(wallet, SUNSWAP_ADDRESS)
    if amount >= approve_amount / 2:
        logger.info("already approved")
        return None
    txn = (
        contract.functions.approve(SUNSWAP_ADDRESS, approve_amount)
        .with_owner(wallet)
        .fee_limit(100 * 1000000)
        .build()
        .sign(PrivateKey(bytes.fromhex(private_key)))
    )
    result = txn.broadcast().wait()
    if result["receipt"]["result"] == "SUCCESS":
       logger.info("transaction ok: {0}".format(result))
    else:
       logger.error("transaction error: {0}".format(result))
    return result

def query_price(tron: Tron, token_path: list) -> Decimal:
    contract = tron.get_contract(SUNSWAP_ADDRESS)
    contract_token = tron.get_contract(token_path[0])
    contract_token.abi = TOKEN_ABI
    decimals = contract_token.functions.decimals()
    amount = contract.functions.getAmountsOut(1 * 10 ** decimals, token_path)
    amount_in = Decimal(amount[0]) / (10 ** decimals)
    amount_out = Decimal(amount[1]) / (10 ** 6)
    return amount_out / amount_in

def swap_token(tron: Tron, amount_in: Decimal, token_path: list, wallet: str, private_key: str) -> Decimal:
    approve_erc20_to_sunswap(tron, wallet, private_key, token_path[0])

    contract = tron.get_contract(SUNSWAP_ADDRESS)

    contract_token = tron.get_contract(token_path[0])
    contract_token.abi = TOKEN_ABI

    decimals = contract_token.functions.decimals()
    amount_in = int(amount_in * 10 ** decimals)

    amount = contract.functions.getAmountsOut(amount_in, token_path)

    minimum_out = int(amount[1] * (1 - Decimal(SLIPPAGE) - Decimal("0.003")))  # С учетом слиппиджа
    deadline = datetime.now() + timedelta(minutes=5)

    txn = (contract.functions.swapExactTokensForETH(
        amount_in, minimum_out, token_path, wallet, int(deadline.timestamp())
    ).with_owner(wallet).fee_limit(100 * 1000000).build().sign(PrivateKey(bytes.fromhex(private_key))))

    result = txn.broadcast().wait()
    if result["receipt"]["result"] == "SUCCESS":
        logger.info("transaction ok: {0}".format(result))
        amount_out = Decimal(amount[1]) / (10 ** 6)
        fee = result.get('fee', 0)
        energy_usage_total = result['receipt'].get('energy_usage_total', 0)
        total_fee_trx = fee / 1_000_000
        energy_fee_trx = energy_usage_total / 1_000_000
        logger.info(f"Total fee: {total_fee_trx} TRX")
        logger.info(f"Energy fee: {energy_fee_trx} TRX")
        return amount_out, total_fee_trx
    else:
        logger.error("transaction error: {0}".format(result))
        sys.exit(1)

def balance_TRX():
    private_key = PRIVATE_KEY
    wallet = get_wallet_address(private_key)
    tron = Tron(HTTPProvider(timeout=30, api_key=API_KEY))
    balance_tron = tron.get_account_balance(wallet)
    balance_tron = Decimal(balance_tron)
    logger.log("BALANCE", "TRX balance: {0}".format(balance_tron))
    return balance_tron

def balance_token():
    private_key = PRIVATE_KEY
    tron = Tron(HTTPProvider(timeout=30, api_key=API_KEY))
    wallet = get_wallet_address(private_key)
    balance = erc20_balance(tron, wallet, TOKEN_ADDRESS)
    balance = Decimal(balance)
    logger.log("BALANCE", "Token balance: {0}".format(balance))
    return balance

def main_swap(limit_price, balance):
    private_key = PRIVATE_KEY
    tron = Tron(HTTPProvider(timeout=30, api_key=API_KEY))
    wallet = get_wallet_address(private_key)
    token_path = [TOKEN_ADDRESS, ""]
    price = query_price(tron, token_path)
    logger.info(f"Current price: {price} TOKEN/TRX")

    if price <= limit_price:
            logger.info(f"Price is acceptable. Swapping {balance} tokens.")
            logger.info(f"Current price: {price} TOKEN/TRX")
            trx_received, fee = swap_token(tron, balance, token_path, wallet, private_key)
            return trx_received, fee, price
    else:
            logger.info(f"Current price {price} is above limit price {limit_price}. Recalculating...")
            return None

def test_price():
    token_path = [TOKEN_ADDRESS, ""]
    tron = Tron(HTTPProvider(timeout=30, api_key=API_KEY))
    price = query_price(tron, token_path)
    fee_percent = Decimal('0.003')
    price_fee = price / (Decimal('1') - fee_percent)
    price_fee1 = truncate(price_fee, 5)
    print(price_fee1)

def test_get_amount_out(tron: Tron, amount_in: Decimal, token_path: list) -> Decimal:
    contract = tron.get_contract(SUNSWAP_ADDRESS)
    contract_token = tron.get_contract(token_path[0])
    contract_token.abi = TOKEN_ABI
    decimals = contract_token.functions.decimals()
    amount_in = int(amount_in * 10 ** decimals)
    amount = contract.functions.getAmountsOut(amount_in, token_path)
    amount_out = Decimal(amount[1]) / (10 ** 6)
    print (amount_out)

if __name__ == '__main__':
 while True:
    test_price()
 token_path = [TOKEN_ADDRESS, ""]
 tron = Tron(HTTPProvider(timeout=30, api_key=API_KEY))
 amount_in = Decimal('00')
 test_get_amount_out(tron, amount_in, token_path)