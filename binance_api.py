from binance.client import Client
import binance.exceptions
from binance.enums import *
from dotenv import load_dotenv
import helpful_scripts as hs
import os
import json

# Load variables from .env file
load_dotenv()
SHEET_NAME = os.getenv("SHEET_NAME")

def get_client(test):
    if test == "y":
        API_KEY = os.getenv("TEST_API_KEY")
        SECRET_KEY = os.getenv("TEST_SECRET_KEY")
        FILE_PATH = os.getenv("TEST_FILE_PATH")
    else:
        API_KEY = os.getenv("API_KEY")
        SECRET_KEY = os.getenv("SECRET_KEY")
        FILE_PATH = os.getenv("FILE_PATH")   

    # Replace YOUR_API_KEY and YOUR_SECRET_KEY with your actual API keys
    client = Client(api_key=API_KEY, api_secret=SECRET_KEY, testnet=True)   
    return client  

def get_asset_balance(input_obj, test):
    # Coins to get balances for
    coins = input_obj['curr_holdings']['asset']
    # Generate a binance client
    client = get_client(test)

    # Get USD prices for each coin
    prices = client.get_all_tickers()
    usd_prices = {price['symbol']: price['price'] for price in prices if price['symbol'].endswith('BUSD')}

    # Get asset balance and USD value for each coin
    total_usd_value = 0
    coins_balance = []
    coins_usdprice = []
    assets_to_remove = []  # list to store assets to be removed
    for coin in coins:
        if coin != 'BUSD' and coin != 'USDT':
            asset_balance = client.get_asset_balance(asset=coin)
            if asset_balance is not None and float(asset_balance['free']) > 0:
                usd_price = float(usd_prices[f'{coin}BUSD'])
                usd_value = float(asset_balance['free']) * usd_price
                total_usd_value += usd_value
                coins_balance.append(float(asset_balance['free']))
                coins_usdprice.append(usd_value)
            else:
                assets_to_remove.append(coin)  # add asset to be removed
        else:
            asset_balance = client.get_asset_balance(asset=coin)
            if asset_balance is not None:
                coins_balance.append(float(asset_balance['free']))
                coins_usdprice.append(float(asset_balance['free']))
                total_usd_value += float(asset_balance['free'])

    # remove assets to be removed
    for asset in assets_to_remove:
        coins.remove(asset)

    input_obj['curr_holdings']['asset'] = coins
    input_obj['curr_holdings']['coins'] = coins_balance
    input_obj['curr_holdings']['usdprice'] = coins_usdprice

    input_obj['Total USD Value'] = {'usdprice': total_usd_value}

    return input_obj

def market_order_amt(symbol, side, amount, test):
    # print(f"tradepair: {symbol}")
    # Generate a binance client
    client = get_client(test)

    symbol_info = client.get_symbol_info(symbol=symbol)
    # symbol_info_json = json.dumps(symbol_info, indent=2)
    # print(f"symbol info: {symbol_info_json}")
    # print(f"symbol: {symbol_info}")

    # Check if symbol info is None
    if symbol_info is None:
        return 0

    try: 
        precision = symbol_info['baseAssetPrecision']
    except ValueError:
        precision = 8

    filters = symbol_info['filters']
    for filter_dict in filters:
        if filter_dict["filterType"] == "MIN_NOTIONAL" or filter_dict["filterType"] == "NOTIONAL" :
            min_notional = float(filter_dict["minNotional"])
        if filter_dict["filterType"] == "LOT_SIZE":
            min_qty_lot = float(filter_dict['minQty'])
            max_qty_lot = float(filter_dict['maxQty'])
        if filter_dict["filterType"] == "MARKET_LOT_SIZE":
            max_qty_mkt = float(filter_dict['maxQty'])

    ticker = client.get_symbol_ticker(symbol=symbol)
    price = ticker['price']
    maxprice = float(max_qty_mkt) * float(price) * 0.95
    minprice = float(min_qty_lot) * float(price) * 1.1
    total_trade = 0

    try:
        # print(f"amount: {amount} - minAmt: {min_notional}")
        if float(amount) > float(min_notional):
            if maxprice < amount:
                remaining_amount = amount
                while remaining_amount > min_notional:
                    ticker = client.get_symbol_ticker(symbol=symbol)
                    price = float(ticker['price'])
                    # print(f"checks: {price} - {max_qty_mkt}")
                    trade_amt = round(max_qty_mkt * price * 0.95, precision)
                    if maxprice > float(remaining_amount):
                        trade_amt = round(float(remaining_amount),precision)
                    if side == "sell":
                        # print(f"selling: {symbol} - {trade_amt}")
                        trade_amt = market_order_amt_sell(symbol, trade_amt, test)
                        total_trade += trade_amt
                        remaining_amount -= trade_amt
                    else:
                        # print(f"buying: {symbol} - {trade_amt}")
                        trade_amt = market_order_amt_buy(symbol, trade_amt, test)
                        total_trade += trade_amt
                        remaining_amount -= trade_amt                
            else:
                if side == "sell":
                    total_trade = market_order_amt_sell(symbol, amount, test)
                else:
                    total_trade = market_order_amt_buy(symbol, amount, test)
            return total_trade
        else:
            print(f"min notional amt: {min_notional} is larger the trade amount: {amount}, skipped trading")
            return 0
    except ValueError:
        raise ValueError("Error making the trade request")


def market_order_qty(symbol, side, qty, test):
    # Generate a binance client
    client = get_client(test)

    symbol_info = client.get_symbol_info(symbol=symbol)
    # symbol_info_json = json.dumps(symbol_info, indent=2)
    # print(f"symbol info: {symbol_info_json}")
    precision = 8
    # print(f"precision: {precision}")
    max_qty_mkt = float(symbol_info['filters'][4]['maxQty'])
    max_qty_lot = float(symbol_info['filters'][1]['maxQty'])
    min_qty_lot = float(symbol_info['filters'][1]['minQty'])
    total_trade = 0

    try: 
        if qty > min_qty_lot:
            if max_qty_mkt < qty:
                remaining_qty = qty
                while remaining_qty > min_qty_lot:
                    trade_qty = round(float(max_qty_mkt) , precision)
                    if max_qty_mkt > float(remaining_qty):
                        trade_qty = round(float(remaining_qty),precision)
                    if side == "sell":
                        trade_amount = market_order_qty_sell(symbol, trade_qty, test)
                        total_trade += trade_amount
                        remaining_qty -= trade_amount
                    else:
                        trade_amount = market_order_qty_buy(symbol, trade_qty, test)
                        total_trade += trade_amount
                        remaining_qty -= trade_amount                
            else:
                if side == "sell":
                    total_trade = market_order_qty_sell(symbol, qty, test)
                else:
                    total_trade = market_order_qty_buy(symbol, qty, test)
            return total_trade
        else:
            print("min qty is larger the trade quantity, skipped trading")
            return 0
    except ValueError:
        return 0

def market_order_amt_buy(symbol, amount, test):
    # Generate a binance client
    client = get_client(test)

    order = client.create_order(
            symbol=symbol,
            side=Client.SIDE_BUY,
            type=Client.ORDER_TYPE_MARKET,
            quoteOrderQty=amount
        )
    order_amt = float(order['cummulativeQuoteQty'])
    return order_amt

def market_order_qty_buy(symbol, quantity, test):
    # Generate a binance client
    client = get_client(test)

    order = client.create_order(
            symbol=symbol,
            side=Client.SIDE_BUY,
            type=Client.ORDER_TYPE_MARKET,
            quantity=quantity
        )
    order_amt = float(order['cummulativeQuoteQty'])
    return order_amt


def market_order_amt_sell(symbol, amount, test):
    # Generate a binance client
    client = get_client(test)

    order = client.create_order(
            symbol=symbol,
            side=Client.SIDE_SELL,
            type=Client.ORDER_TYPE_MARKET,
            quoteOrderQty=amount
        )
    order_amt = float(order['cummulativeQuoteQty'])
    return order_amt

def market_order_qty_sell(symbol, quantity, test):
    # Generate a binance client
    client = get_client(test)

    order = client.create_order(
            symbol=symbol,
            side=Client.SIDE_SELL,
            type=Client.ORDER_TYPE_MARKET,
            quantity=quantity
        )
    order_amt = float(order['cummulativeQuoteQty'])
    return order_amt