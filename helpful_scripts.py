import pandas as pd
import requests
import ezodf
import binance_api as ba

def get_file_dtls(file_path, sheet_name):
    cols = ['Current Holdings', 'Allocation', 'Percent', 'Alloc [cons]', 'c.Percent', 'Alloc [SS]', 'ss.Percent', 'Alloc [Ex]', 'ex.Percent']

    df = pd.read_excel(file_path, sheet_name=sheet_name, usecols=cols)

    # Drop rows with all NaN values
    df.dropna(how='all', inplace=True)

    # Get data for each column and remove nan values
    holdings = df['Current Holdings'].dropna().values
    allocation = df['Allocation'].dropna().values
    percent = df['Percent'].dropna().values
    alloc_cons = df['Alloc [cons]'].dropna().values
    c_percent = df['c.Percent'].dropna().values
    alloc_ss = df['Alloc [SS]'].dropna().values
    ss_percent = df['ss.Percent'].dropna().values
    alloc_ex = df['Alloc [Ex]'].dropna().values
    ex_percent = df['ex.Percent'].dropna().values

    # Construct output object
    out_obj = {
        "curr_holdings": { "asset": holdings.tolist(), "coins": [], "usdprice": []},
        "allocation": { "name": allocation.tolist(), "percent": percent.tolist()},
        "conservative_allocation": { "asset": alloc_cons.tolist(), "percent": c_percent.tolist()},
        "small_spec_allocation": {"asset": alloc_ss.tolist(), "percent": ss_percent.tolist()},
        "experimental_allocation": {"asset": alloc_ex.tolist(), "percent": ex_percent.tolist()},
    }

    return out_obj

def copy_sheet_to_new_tab(file_path, sheet_name, new_sheet_name):
    # Load the document and get the sheet to copy
    doc = ezodf.opendoc(file_path)
    sheet = doc.sheets[sheet_name]
    
    # Create a new sheet and copy over the content
    new_sheet = doc.sheets.insert(0, new_sheet_name)
    for row_idx, row in enumerate(sheet.rows()):
        for col_idx, cell in enumerate(row):
            new_sheet[row_idx][col_idx].set_value(cell.value)

    # Save the changes to the document
    doc.save()


def calculate_allocation_values(obj):
    total_usd_value = obj['Total USD Value']['usdprice']
    
    # Calculate allocation values
    allocation = obj['allocation']
    allocation_percent = allocation['percent']
    allocation_usd_value = [round(total_usd_value * p, 4) for p in allocation_percent]
    allocation['usdvalue'] = allocation_usd_value
    
    # Calculate conservative allocation values
    conservative_allocation = obj['conservative_allocation']
    conservative_percent = conservative_allocation['percent']
    conservative_usd_value = [round(total_usd_value * p * allocation_percent[0], 4) for p in conservative_percent]
    conservative_allocation['usdvalue'] = conservative_usd_value
    
    # Calculate small speculative allocation values
    small_spec_allocation = obj['small_spec_allocation']
    small_spec_percent = small_spec_allocation['percent']
    small_spec_usd_value = [round(total_usd_value * p * allocation_percent[1], 4) for p in small_spec_percent]
    small_spec_allocation['usdvalue'] = small_spec_usd_value
    
    # Calculate experimental allocation values
    experimental_allocation = obj['experimental_allocation']
    experimental_percent = experimental_allocation['percent']
    experimental_usd_value = [round(total_usd_value * p * allocation_percent[2], 4) for p in experimental_percent]
    experimental_allocation['usdvalue'] = experimental_usd_value
    
    # Return modified object
    return obj

def new_allocations(curr_holdings):
    total_holdings = {}
    new_allocations_total = 0
    
    # Loop through each allocation type
    for allocation_type in ['conservative_allocation', 'small_spec_allocation', 'experimental_allocation']:
        assets = curr_holdings[allocation_type]['asset']
        usd_values = curr_holdings[allocation_type]['usdvalue']
        
        # Loop through each asset in the allocation type
        for i in range(len(assets)):
            asset = assets[i]
            usd_value = usd_values[i]
            new_allocations_total += usd_value
            
            # If the asset is already in the total_holdings dictionary, add the usd_value to the existing value
            if asset in total_holdings:
                total_holdings[asset] += usd_value
            # Otherwise, add the asset to the dictionary with the usd_value as the value
            else:
                total_holdings[asset] = usd_value
    
    # Round the USD value to 2 decimal places
    for asset in total_holdings:
        total_holdings[asset] = round(total_holdings[asset], 2)
    
    # print(f"New Allocations Total: {new_allocations_total:,.2f}")
    return total_holdings

def moves_to_do(current, target):
    out_obj = {}
    for asset in current['asset']:
        if asset in target:
            idx = current['asset'].index(asset)
            curr_usd_value = float(current['usdprice'][idx])
            target_usd_value = float(target[asset])
            if (target_usd_value - curr_usd_value) < 0 :
                out_obj[asset] = {'trade': 'sell', 'usd': curr_usd_value - target_usd_value, 'all': 'no'}
            elif (target_usd_value - curr_usd_value) > 0 :
                out_obj[asset] = {'trade': 'buy', 'usd': target_usd_value - curr_usd_value, 'all': 'no'}
            else:
                out_obj[asset] = {'trade': 'no'}
        else:
            idx = current['asset'].index(asset)
            curr_usd_value = current['usdprice'][idx]
            coins = current['coins'][idx]
            out_obj[asset] = {'trade': 'sell', 'usd': curr_usd_value, 'all': 'yes', 'coins': coins}
    
    for asset in target:
        if asset not in current['asset']:
            out_obj[asset] = {'trade': 'buy', 'usd': target[asset], 'all': 'no'}
            
    return out_obj

def check_valid_assets(obj):
    invalid_assets = {'asset': []}

    for allocation in ['small_spec_allocation', 'experimental_allocation']:
        assets_to_remove = []
        for i, asset in enumerate(obj[allocation]['asset']):
            if asset != 'CASH':
                url = f"https://api.binance.com/api/v3/ticker/price?symbol={asset}USDT"
                response = requests.get(url)
                if response.status_code != 200:
                    url = f"https://api.binance.com/api/v3/ticker/price?symbol={asset}BUSD"
                    response = requests.get(url)
                    if response.status_code != 200:
                        invalid_assets['asset'].append(asset)
                        assets_to_remove.append(i)
                    else:
                        obj[allocation]['asset'][i] = asset + 'BUSD'
        for index in sorted(assets_to_remove, reverse=True):
            obj[allocation]['asset'].pop(index)
            obj[allocation]['percent'].pop(index)
        total_percent = sum(obj[allocation]['percent'])
        obj[allocation]['percent'] = [round(p/total_percent, 4) for p in obj[allocation]['percent']]
    
    obj['invalid_assets'] = invalid_assets
    return obj


def generate_trade_summary(trades):
    summary = "======================================================================\n"
    summary += "The following trades would be performed:\n"
    trade_list = []
    net_total = 0  # Initialize net total to zero
    
    for coin, data in trades.items():
        if data['usd'] == 0:
            continue
        if data['trade'] == 'sell':
            if coin == 'USDT' or coin == 'BUSD':
                usd_amount = -1 * data['usd']  # Set sell amounts to negative
                usd_amt_display = data['usd']
                trade_list.insert(0, f"- Coin {coin} at amt ${usd_amt_display:,.3f} is available")
            else:
                usd_amount = -1 * data['usd']  # Set sell amounts to negative
                trade_list.insert(0, f"- Sell {coin} at amt ${usd_amount:,.3f} ")
        elif data['trade'] == 'buy':
            if coin == 'USDT' or coin == 'BUSD':
                usd_amount = data['usd']
                trade_list.append(f"- Coin {coin} at amt ${usd_amount:,.3f} would be available")
            else:
                usd_amount = data['usd']
                trade_list.append(f"- Buy {coin} at amt ${usd_amount:,.3f} ")                
        net_total += usd_amount  # Add amount to net total
    
    # Check if net total is not within tolerance of zero
    if abs(net_total) > 0.05:
        print("WARNING: Net total is not zero.")
    
    if len(trade_list) == 0:
        return "No trades to perform."
    
    summary += '\n'.join(trade_list) + f"\n\nNet total: {net_total:,.3f} USD\n"
    summary += "======================================================================\n"
    summary += "Do you confirm these actions (y/n)? "
    response = input(summary).strip().lower()
    return response


def perform_trade_market(trade_dict):
    # Separate the trades into sell and buy
    sell_trades = []
    buy_trades = []
    for asset, trade in trade_dict.items():
        if asset == 'CASH':
            continue
        if trade['trade'] == 'sell':
            sell_trades.append(asset)
        elif trade['trade'] == 'buy':
            buy_trades.append(asset)
        else:
            raise ValueError('Invalid trade type')
        
    # print(f"sells: {sell_trades}")
    # print(f"buys: {buy_trades}")

    # Perform sell trades
    total_sell_amount = 0
    sell = 'amt'
    for asset in sell_trades:
        for asset2, trade in trade_dict.items():
            if asset2 == asset:
                if trade['all'] == 'yes':
                    quantity = trade['coins']
                    sell = 'qty'
                else:
                    quantity = trade['usd']
                    sell = 'amt'

        symbol = f"{asset}USDT"
        quantity = round(quantity, 3)
        if asset != 'USDT' and asset != 'BUSD':
            try: 
                if sell == 'amt':
                    sell_amount = ba.market_order_amt(symbol, "sell", quantity)
                else: 
                    sell_amount = ba.market_order_qty(symbol, "sell", quantity)
                total_sell_amount += sell_amount
                print(f"Sold {asset} for {sell_amount} USDT")
            except ValueError:
                print(f"Error trading {asset}")

    # Perform buy trades
    buy = 'amt'
    if len(buy_trades) >= 2:
        buy_budget = total_sell_amount
        for asset in buy_trades[:-1]:
            # print(f"asset to buy: {asset}")
            for asset2, trade in trade_dict.items():
                if asset2 == asset:
                    if trade['all'] == 'yes':
                        quantity = trade['coins']
                        buy = 'qty'
                    else:
                        quantity = trade['usd']
                        buy = 'amt'        
            # Convert USDT to asset
            symbol = f"{asset}USDT"
            quantity = round(quantity, 3)
            if asset != 'USDT' and asset != 'BUSD':  
                try:          
                    if buy == 'amt':
                        buy_amt = ba.market_order_amt(symbol, "buy", quantity)
                    else: 
                        buy_amt = ba.market_order_qty(symbol, "buy", quantity)
                    buy_budget -= buy_amt
                    print(f"Bought {asset} for {buy_amt} USDT")
                except ValueError:
                    print(f"Error trading {asset}")           


        # Convert remaining USDT to last asset
        usdt_balance = buy_budget
        last_asset = buy_trades[-1]
        # print(f"asset to buy: {asset}")
        for asset2, trade in trade_dict.items():
            if asset2 == last_asset:
                if trade['all'] == 'yes':
                    quantity = trade['coins']
                    buy = 'qty'
                else:
                    quantity = trade['usd']
                    buy = 'amt'

        symbol = f"{last_asset}USDT"
        if usdt_balance > quantity:
            quantity = usdt_balance
        quantity = round(quantity, 3)
        if asset != 'USDT' and asset != 'BUSD':    
        # print(f"buying {symbol} @qty: {quantity}")
            try:
                if buy == 'amt':
                    buy_amt = ba.market_order_amt(symbol, "buy", quantity)
                else: 
                    buy_amt = ba.market_order_qty(symbol, "buy", quantity)
                buy_budget -= buy_amt
                print(f"Bought {last_asset} for {buy_amt} USDT") 
            except ValueError:
                print(f"Error trading {asset}")   

    elif len(buy_trades) == 1:
        usdt_balance = total_sell_amount
        asset = buy_trades[0]
        # print(f"asset to buy: {asset}")
        for asset2, trade in trade_dict.items():
            if asset2 == asset:
                if trade['all'] == 'yes':
                    quantity = trade['coins']
                    buy = 'qty'
                else:
                    quantity = trade['usd']
                    buy = 'amt'

        symbol = f"{asset}USDT"
        if usdt_balance > quantity:
            quantity = usdt_balance
        quantity = round(quantity, 3)
        if asset != 'USDT' and asset != 'BUSD':        
            # print(f"buying {symbol} @qty: {quantity}")
            try:
                if buy == 'amt':
                    buy_amt = ba.market_order_amt(symbol, "buy", quantity)
                else: 
                    buy_amt = ba.market_order_qty(symbol, "buy", quantity)
                print(f"Bought {asset} for {buy_amt} USDT") 
            except ValueError:
                print(f"Error trading {asset}")   




