import helpful_scripts as hs
import binance_api as ba
import createNewFile as cNF
from dotenv import load_dotenv
import os

# Load variables from .env file
load_dotenv()
FILE_PATH = os.getenv("TEST_FILE_PATH")
#Legit
# FILE_PATH = os.getenv("FILE_PATH")
SHEET_NAME = os.getenv("TEST_SHEET_NAME")

relabance_obj = hs.get_file_dtls(FILE_PATH, SHEET_NAME)
print("======================================================================")
print(f"init obj: {relabance_obj}")

#Perform validation on the percent allocations if all is 100% before doing any computations
try:
    hs.validate_allocation(relabance_obj)
except ValueError as e:
    print(e)
    print("Please correct percent allocations on the file and re-run the automation")
else:
    relabance_obj = hs.check_valid_assets(relabance_obj)
    print("======================================================================")
    print(f"check valid: {relabance_obj}")

    relabance_obj = ba.get_asset_balance(relabance_obj, "y")
    print("======================================================================")
    print(f"asset_balance: {relabance_obj}")

    relabance_obj = hs.calculate_allocation_values(relabance_obj)
    print("======================================================================")
    print(f"allocations: {relabance_obj}")

    new_allocations = hs.new_allocations(relabance_obj)
    print("======================================================================")
    print(f"new allocs: {new_allocations}")

    moves = hs.moves_to_do(relabance_obj['curr_holdings'], new_allocations)
    print("======================================================================")
    print(f"moves: {moves}")

    trade_cont = hs.generate_trade_summary(moves)
    # print("======================================================================")
    # print(f"moves: {trade_cont}")

    if trade_cont == "y":
        hs.perform_trade_market(moves, "y")

        cNF.create_new_file(FILE_PATH, SHEET_NAME, new_allocations)
        print("======================================================================")
    else:
        print("======================================================================")    
        print("No Trades Performed")


