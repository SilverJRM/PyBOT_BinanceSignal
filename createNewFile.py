import pandas as pd
import datetime
import os
import numpy as np

def create_new_file(file_path, sheet_name, new_holdings):
    # Read data from input file
    df = pd.read_excel(file_path, sheet_name=sheet_name)

    # Filter out NaN values
    df = df.dropna(how='all')

    # Get data for each column
    allocation = df['Allocation'].values
    percent = df['Percent'].values
    alloc_cons = df['Alloc [cons]'].values
    c_percent = df['c.Percent'].values
    alloc_ss = df['Alloc [SS]'].values
    ss_percent = df['ss.Percent'].values
    alloc_ex = df['Alloc [Ex]'].values
    ex_percent = df['ex.Percent'].values

    # Get data from new_holdings
    new_holdings_list = []
    for key, value in new_holdings.items():
        if value != 0:
            if key == 'CASH':
                new_holdings_list.append(key)
            else:
                new_holdings_list.append(key.upper())

    # Replace holdings with new_holdings_list
    holdings = new_holdings_list

    # Add NaN values to holdings to match length of other columns
    num_rows = df.shape[0]
    num_holdings = len(holdings)
    if num_holdings < num_rows:
        num_missing = num_rows - num_holdings
        holdings += [np.nan] * num_missing

    # Create a new sheet with the given name and write data to it
    date_str = datetime.datetime.now().strftime('%Y%m%d')
    old_file_name = os.path.basename(file_path)
    old_file_name_without_ext, ext = os.path.splitext(old_file_name)
    new_file_name = f"{date_str}_{old_file_name_without_ext}{ext}"
    new_file_path = os.path.join(os.path.dirname(file_path), new_file_name)

    if os.path.exists(new_file_path):
        os.remove(new_file_path)

    if os.path.exists(file_path):
        # Move the old file to a new file with the date attached
        os.rename(file_path, new_file_path)

    with pd.ExcelFile(new_file_path) as old_file:
        old_trade_df = pd.read_excel(old_file, sheet_name='NewTrade')

    # Create a new file with the name of the old file and write data to it
    with pd.ExcelWriter(file_path) as writer:
        pd.DataFrame(old_trade_df).to_excel(writer, sheet_name='OldTrade', index=False)
        pd.DataFrame({'Current Holdings': holdings, 'Allocation': allocation,
                      'Percent': percent, 'Alloc [cons]': alloc_cons, 'c.Percent': c_percent,
                      'Alloc [SS]': alloc_ss, 'ss.Percent': ss_percent, 'Alloc [Ex]': alloc_ex,
                      'ex.Percent': ex_percent}).to_excel(writer, sheet_name='NewTrade', index=False)

    print(f"New file created: {file_path}")



def revert_files(file_path):

    date_str = datetime.datetime.now().strftime('%Y%m%d')
    old_file_name = os.path.basename(file_path)
    old_file_name_without_ext, ext = os.path.splitext(old_file_name)
    new_file_name = f"{date_str}_{old_file_name_without_ext}{ext}"
    new_file_path = os.path.join(os.path.dirname(file_path), new_file_name)

    if os.path.exists(new_file_path) and os.path.exists(file_path):
        if os.path.exists(file_path):
            os.remove(file_path)

        if os.path.exists(new_file_path):
            #revert the files back to old 
            os.rename(new_file_path, file_path)
        print("revert file completed!")
    else:
        print("nothing to revert..")