import pandas as pd
import datetime
import os
import numpy as np

def create_new_file(file_path, sheet_name, new_holdings):
    # print("creating new file....")
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
    
    if os.path.exists(file_path):
        overwrite = "y"
        if overwrite == "y":
            os.remove(file_path)
        else:
            counter = 1
            while os.path.exists(new_file_path):
                counter += 1
                new_file_name = f"{date_str}_{old_file_name_without_ext}_{counter}{ext}"
                new_file_path = os.path.join(os.path.dirname(file_path), new_file_name)
            print(f"Creating new file: {new_file_name}")
            file_path = new_file_path

    with pd.ExcelWriter(file_path) as writer:
        df.to_excel(writer, sheet_name='OldTrade', index=False)
        pd.DataFrame({'Current Holdings': holdings, 'Allocation': allocation,
                      'Percent': percent, 'Alloc [cons]': alloc_cons, 'c.Percent': c_percent,
                      'Alloc [SS]': alloc_ss, 'ss.Percent': ss_percent, 'Alloc [Ex]': alloc_ex,
                      'ex.Percent': ex_percent}).to_excel(writer, sheet_name='NewTrade', index=False)
    print("new file created!!")
