#import scrapy
import pandas as pd
import requests
from bs4 import BeautifulSoup
import json
import numpy

def main():
    # read the airline accident data from the excel file, we want sheet 29 from the file
    # col 13: Registration Number (to get airline carrier)
    # col 17: Flight Regulation (commercial, private, charter, etc; we are looking for commercial)
    #accident_df = pd.read_excel("AviationAccidentStatistics_2003-2022_20231228.xlsx", sheet_name=28)

    # next we'll read the csv file of customer review data
    # col 1: Airline name
    # col 5: If the review is verified
    # col 6: Review text we will be analyzing (the core of the project)
    #review_df = pd.read_csv("Airline_review.csv")

    # next we need to use the registration numbers from the accident df to get the airline carrier for that flight
    get_url = 'https://registry.faa.gov/aircraftinquiry/Search/NNumberInquiry'
    post_url = 'https://registry.faa.gov/aircraftinquiry/Search/NNumberResult'

    # will not work if user-agent is python requests
    headers = {
        "user-agent" : "PostmanRuntime/7.37.3"
    }

    test_num = 'N16571'
    payload = {
        "NNumbertxt" : test_num
    }

    session = requests.session()

    response = session.get(get_url, headers=headers)
    response = session.post(post_url, headers=headers, data=payload)

    soup = BeautifulSoup(response.text, features='html.parser')
    #print(soup)
    print(response.text)

    # make some pretty graphs using numpy or something

def test_print_df_cols(df):
    i = 0
    print("cols:")
    for col in df.columns:
        print(f"{i}: {col}")
        i += 1

if __name__ == '__main__':
    main()