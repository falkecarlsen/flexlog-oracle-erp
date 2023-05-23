from datetime import datetime
from typing import List, Union, Tuple

import pandas as pd
from pandas import DataFrame

"""
todo:
    - add sub dataframes
    - add mean of login and logout times
    - add total hours for every month per sub
    - correspond expected hours per month (working days * 7.4)
    - generate html clickable report to use for reporting hours
    - add statistics to keep track of overtime
    - add constraints to when worked hours may not be reported, and move them to allowed working days
"""


# timesheet class holding a 'base' dataframe as total hours, and some number of 'sub' dataframes for specific projects
class Timesheet:
    total: DataFrame
    sub: DataFrame

    @staticmethod
    def convert_date_to_datetime(df: DataFrame) -> DataFrame:
        df['Date'] = pd.to_datetime(df['Date'], format='%d/%m/%Y')
        return df

    def __init__(self, total_csv_filename: str):
        self.total = self.convert_date_to_datetime(pd.read_csv(total_csv_filename, sep=';', decimal=','))
        # set index to date
        self.total.set_index('Date', inplace=True)

    def add_sub(self, sub_csv_filename: str):
        self.sub = self.convert_date_to_datetime(pd.read_csv(sub_csv_filename, sep=';', decimal=','))
        # set index to date
        self.sub.set_index('Date', inplace=True)

    def mean_login_logout(self, range: Tuple[datetime, datetime] = None) -> Union[None, datetime.time]:
        if not range:
            return (pd.to_datetime(self.total['Login'].dropna(), format='%H.%M').mean().strftime('%H:%M'),
                    pd.to_datetime(self.total['Logout'].dropna(), format='%H.%M').mean().strftime('%H:%M'))
        else:
            # restrict login and logout dataframes to be within range
            start = range[0]
            stop = range[1]
            res: DataFrame = self.total.loc[start:stop]
            print(res[['Login', 'Logout']])
            return (pd.to_datetime(res['Login'].dropna(), format='%H.%M').mean().strftime('%H:%M'),
                    pd.to_datetime(res['Logout'].dropna(), format='%H.%M').mean().strftime('%H:%M'))

    # total hours for every month
    def total_hours_per_month(self) -> List[float]:
        # define months in range of total dataframe
        months = pd.date_range(start=self.total.index.min(), end=self.total.index.max(), freq='M')
        # prune months with no hours
        months = [month for month in months if month in self.total.index]

        print(months)


    def erp_html_render(self):
        pass


hours = Timesheet('aau-RA-21_11_2022-12_05_2023.csv')
hours.add_sub('aau-CEDAR-07_03_2023-11_05_2023.csv')

print(hours.mean_login_logout((datetime(2023, 3, 1), datetime(2023, 5, 11))))
print(hours.total_hours_per_month())


hours.erp_html_render()
