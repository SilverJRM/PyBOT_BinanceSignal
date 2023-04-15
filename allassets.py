import argparse
from binance.client import Client
from binance.enums import *
from dotenv import load_dotenv
import os
import json
import helpful_scripts as hs
import binance_api as ba

# Load variables from .env file
load_dotenv()
API_KEY = os.getenv("API_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")

# Replace YOUR_API_KEY and YOUR_SECRET_KEY with your actual API keys
client = Client(api_key=API_KEY, api_secret=SECRET_KEY)

def get_balances(all_assets):
    # Get USD prices for all coins
    prices = client.get_all_tickers()
    usd_prices = {price['symbol']: float(price['price']) for price in prices if price['symbol'].endswith('BUSD')}

    # Get all asset balances
    balances = client.get_account()['balances']

    # Determine which assets to process
    assets = []
    if all_assets == "y":
        assets = [balance['asset'] for balance in balances]
    else:
        assets = ['BTC', 'ETH', 'USDT', 'ICX', 'FOR', 'LINA', 'ACH']  # Replace with your own list of assets to process

    # Calculate USD value of each non-zero balance
    total_usd_value = 0
    for balance in balances:
        asset = balance['asset']
        free_balance = float(balance['free'])
        locked_balance = float(balance['locked'])

        if asset in assets and free_balance + locked_balance > 0:
            try:
                if asset != 'BUSD' and asset != 'USDT':
                    usd_value = (free_balance + locked_balance) * usd_prices[f'{asset}BUSD']
                else:
                    usd_value = free_balance + locked_balance
                print(f"{asset} balance: {free_balance + locked_balance:.8f} - in USD: {usd_value:.8f}")
                total_usd_value += usd_value
            except KeyError:
                print(f"{asset} has no StableCoin counterpart")
    print(f"Total value in USD: {total_usd_value:.8f}")

def main(all_assets):
    get_balances(all_assets)

if __name__ == '__main__':
    # Parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', '--all', help='process all assets', default='n')
    args = parser.parse_args()

    # call the main function
    main(args.all)
