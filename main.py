from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Any

import pandas
import pandas as pd
from pandas import DataFrame
import matplotlib.pyplot as plt
from datetimerange import DateTimeRange

"""
todo:
    - add sub dataframes
    - add mean of login and logout times
    - add total hours for every month per sub
    - correspond expected hours per month (working days * 7.4)
    - generate html clickable report to use for reporting hours
    - add statistics to keep track of overtime
    - add constraints to when worked hours may not be reported, and move them to allowed working days

ERP entry has following fields:
- Project: The project name fuzzily matched - also includes the project number
- Finansiering: Ekstern / Intern
- Omkostningstype: Løn
- Analysenummer: 00000
- Dates: CSV DD-MM-YYYY format, but picked via datepicker
- Quantity: The hours worked on those days
- Comments: The description of the work done
"""


@dataclass
class CSVDataFrame:
    timesheet: DataFrame
    project: str
    login_mean: str
    logout_mean: str
    monthly_hours: Dict

    def __init__(self, csv_filename: str):
        self.timesheet = self.convert_date_to_datetime(pd.read_csv(csv_filename, sep=";", decimal=","))
        self.timesheet.set_index("Date", inplace=True)
        self.project = csv_filename.split("-")[1]
        self.calculate_mean_login_logout()
        self.calculate_total_hours_per_month()

    @staticmethod
    def convert_date_to_datetime(df: DataFrame) -> DataFrame:
        df["Date"] = pd.to_datetime(df["Date"], format="%d/%m/%Y")
        return df

    def calculate_mean_login_logout(self, date_range: Tuple[datetime, datetime] = None):
        if not date_range:
            self.login_mean = pd.to_datetime(self.timesheet["Login"].dropna(), format="%H.%M").mean().strftime("%H:%M")
            self.logout_mean = (
                pd.to_datetime(self.timesheet["Logout"].dropna(), format="%H.%M").mean().strftime("%H:%M")
            )

        else:
            start = date_range[0]
            stop = date_range[1]
            res: DataFrame = self.timesheet.loc[start:stop]
            self.login_mean = pd.to_datetime(res["Login"].dropna(), format="%H.%M").mean().strftime("%H:%M")
            self.logout_mean = pd.to_datetime(res["Logout"].dropna(), format="%H.%M").mean().strftime("%H:%M")

    def calculate_total_hours_per_month(self):
        months = pd.date_range(start=self.timesheet.index.min(), end=self.timesheet.index.max(), freq="M")
        hours_per_month = {}
        for month in months:
            if month in self.timesheet.index:
                # Filter the dataframe to include only rows within the current month
                month_df = self.timesheet[self.timesheet.index.month == month.month]
                # get total hours by summing duration for the month_df, ignoring rows with '1.0' in the 'Sick day' column
                total_hours: pandas.Series = month_df["Duration"].loc[month_df["Sick day"] != 1.0]

                # convert stringified hours to timedelta
                def convert_to_timedelta(x: str):
                    try:
                        if not x:
                            return timedelta(0)
                        elif x.isdigit():
                            return timedelta(hours=int(x))
                        else:
                            return pandas.to_timedelta(x.replace(".", ":") + ":00")
                    except Exception as e:
                        print(e)
                        raise

                total_hours = total_hours.apply(lambda x: convert_to_timedelta(x.strip()))
                # sum the timedelta and convert to hours
                total_hours = total_hours.sum().total_seconds() / 3600
                # Add the total hours to the dictionary
                hours_per_month[(month.year, month.month)] = total_hours
        self.monthly_hours = hours_per_month


class Timesheet:
    total: CSVDataFrame
    sub: List[CSVDataFrame] = []

    def __init__(self, total_csv_filename: str):
        self.total = CSVDataFrame(csv_filename=total_csv_filename)

    def add_sub(self, sub_csv_filename: str):
        self.sub.append(CSVDataFrame(csv_filename=sub_csv_filename))

    def hours_last_month(self, year: int = datetime.now().year, month: int = datetime.now().month - 1) -> float:
        return self.total.monthly_hours[(year, month)]

    @staticmethod
    def get_num_workdays_in_month(year: int = datetime.now().year, month: int = datetime.now().month - 1) -> int:
        # Define the Danish workweek (Monday to Friday)
        workweek = pd.bdate_range(start=f"{year}-{month:02d}-01", end=f"{year}-{month:02d}-28")

        # Exclude public holidays and account for weekends (2023 and 2024 from https://www.kalender-365.dk/helligdage/2024.html)
        holidays = pd.to_datetime(
            [
                "2023-01-01",
                "2023-01-06",
                "2023-02-14",
                "2023-02-19",
                "2023-03-26",
                "2023-04-02",
                "2023-04-06",
                "2023-04-07",
                "2023-04-09",
                "2023-04-10",
                "2023-05-05",
                "2023-05-14",
                "2023-05-18",
                "2023-05-28",
                "2023-05-29",
                "2023-06-05",
                "2023-06-23",
                "2023-06-24",
                "2023-10-29",
                "2023-10-31",
                "2023-11-11",
                "2023-12-24",
                "2023-12-25",
                "2023-12-26",
                "2023-12-31",
                "2024-01-01",
                "2024-01-06",
                "2024-02-11",
                "2024-02-14",
                "2024-03-24",
                "2024-03-28",
                "2024-03-29",
                "2024-03-31",
                "2024-04-01",
                "2024-04-26",
                "2024-05-09",
                "2024-05-12",
                "2024-05-19",
                "2024-05-20",
                "2024-06-05",
                "2024-06-23",
                "2024-06-24",
                "2024-10-27",
                "2024-10-31",
                "2024-11-11",
                "2024-12-24",
                "2024-12-25",
                "2024-12-26",
                "2024-12-31",
            ]
        )
        return len([day for day in workweek if day not in holidays])

    def calculate_expected_hours(self, year: int = datetime.now().year, month: int = datetime.now().month - 1) -> float:
        return self.get_num_workdays_in_month(year, month) * 7.4

    def calculate_overtime(self, year: int = datetime.now().year, month: int = datetime.now().month - 1) -> float:
        return self.hours_last_month(year, month) - self.calculate_expected_hours(year, month)

    def plot_surplus_deficit(self):
        # Calculate the surplus/deficit of actual hours against expected hours for each day in hours.total
        hours.total["Surplus/Deficit"] = hours.total.apply(
            lambda row: (
                pd.to_datetime(row["Logout"], format="%H.%M") - pd.to_datetime(row["Login"], format="%H.%M")
            ).total_seconds()
            / 3600
            - 7.4,
            axis=1,
        )

        # Calculate the accumulated overtime
        hours.total["Accumulated Overtime"] = hours.total["Surplus/Deficit"].cumsum()

        # Plot the surplus/deficit and accumulated overtime with different colors for weekends
        fig, ax1 = plt.subplots()

        # Plot surplus/deficit
        hours.total["Surplus/Deficit"].plot(ax=ax1, color="b")
        ax1.set_xlabel("Day")
        ax1.set_ylabel("Surplus/Deficit (hours)", color="b")
        ax1.set_title("Surplus/Deficit of Actual Hours against Expected Hours per Day")

        # Create a secondary y-axis for accumulated overtime
        ax2 = ax1.twinx()
        hours.total["Accumulated Overtime"].plot(ax=ax2, color="r")
        ax2.set_ylabel("Accumulated Overtime (hours)", color="r")

        plt.show()

    def plot_total_and_sub_hours(self):
        # Plot the total number of hours worked
        self.total.timesheet["Duration"].plot(label="Total Hours")

        # Plot the hours worked for each sub project
        for i, sub_df in enumerate(self.sub):
            sub_df["Duration"].plot(label=f"Sub Project {i + 1} Hours")

        plt.xlabel("Date")
        plt.ylabel("Hours Worked")
        plt.title("Total Hours Worked and Sub Project Hours")
        plt.legend()
        plt.show()

    def calculate_erp_report(self, year: int = datetime.now().year, month: int = datetime.now().month - 1):
        # find self.total hours performed in month
        try:
            total_hours = self.total.monthly_hours[year, month]
            print("total hours", total_hours)
        except KeyError:
            print(f"No hours performed in {year}-{month} for total")
            return

        # find self.sub hours performed in month
        sub_hours = {}
        for i, sub in enumerate(self.sub):
            try:
                sub_hours[i] = sub.monthly_hours[year, month]
                print(f"sub hours for {sub.project}", sub_hours[i])
            except KeyError:
                print(f"No hours performed in {year}-{month} for sub project {sub.project}")
                return

        # percentage of total hours for each sub project
        sub_percentage = {}
        for i, sub in enumerate(self.sub):
            sub_percentage[i] = sub_hours[i] / total_hours
            print(f"sub percentage for {sub.project}", sub_percentage[i])

        # percentage of total hours which are not consumed by a subproject
        total_percentage = 1 - sum(sub_percentage.values())
        print("total percentage", total_percentage)

        # create a dictionary of the ERP report
        erp_report = {}
        for i, sub in enumerate(self.sub):
            erp_report[sub.project] = sub_percentage[i]
        erp_report["Total"] = total_percentage

        print(erp_report)


start_a = datetime(2023, 1, 1, 9)
start_b = datetime(2023, 1, 1, 10)

end_a = datetime(2023, 1, 1, 11)
end_b = datetime(2023, 1, 1, 11)

a = DateTimeRange(start_a, end_a)
b = DateTimeRange(start_b, end_b)

print("a intersects b: ", a.is_intersection(b))
print("a intersection b: ", a.intersection(b))
print("a intersection b: ", a.timedelta - a.intersection(b).timedelta)


time_range = DateTimeRange("2015-03-22T10:00:00+0900", "2015-03-22T10:10:00+0900")
x = DateTimeRange("2015-03-22T10:05:00+0900", "2015-03-22T10:15:00+0900")
print(time_range.intersection(x))


exit(0)
hours = Timesheet("aau-RA-21_11_2022-01_06_2023.csv")
hours.add_sub("aau-CEDAR-07_03_2023-31_05_2023.csv")

hours.calculate_erp_report()
