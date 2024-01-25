import pandas as pd


def parse_xlsx():
    file_path = r"..\input.xlsx"
    links = []
    xls = pd.ExcelFile(file_path)
    for sheet_name in xls.sheet_names:
        df = xls.parse(sheet_name)
        third_column = df.iloc[:, 2].tolist()
        links.extend([value for value in third_column if pd.notna(value)])
    return links
