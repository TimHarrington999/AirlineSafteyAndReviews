import os
import pandas as pd
import requests
from bs4 import BeautifulSoup
import pickle
import json
import numpy

def main():
    # read the airline accident data from the excel file, we want sheet 29 from the file
    # col 13: Registration Number (to get airline carrier)
    # col 17: Flight Regulation (commercial, private, charter, etc; we are looking for commercial)
    accident_df = pd.read_excel("AviationAccidentStatistics_2003-2022_20231228.xlsx", sheet_name=28)

    # now we'll create a list of N-Numbers from part 121 airlines from the accident data
    flights = get_commercial_flights(accident_df)

    # next we'll read the csv file of customer review data
    # col 1: Airline name
    # col 5: If the review is verified
    # col 6: Review text we will be analyzing (the core of the project)
    review_df = pd.read_csv("Airline_review.csv")

    file_path = "registration_info.txt"
    if os.path.exists(file_path):
        # file exists, read the data
        with open(file_path, "rb") as file:
            airlines = pickle.load(file)
    else:
        # file does not exist, we need to query the web page
        print("No registration data present, must fetch . . .")
        with open(file_path, "wb") as file:
            airlines = get_registration(flights)
            pickle.dump(airlines, file)

    for nnumber in airlines.keys():
        print(f"{nnumber}: {airlines[nnumber]}")

    # make some pretty graphs using numpy or something

# create a list of just part 121 flights from a df
def get_commercial_flights(df):
    flights = []
    for i in range(len(df)):
        if '121' in df.iloc[i, 17]:
            flights.append(df.iloc[i, 13])

    return flights

# get registration information
def get_registration(flights):
    get_url = 'https://registry.faa.gov/aircraftinquiry/Search/NNumberInquiry'
    post_url = 'https://registry.faa.gov/aircraftinquiry/Search/NNumberResult'

    # will not work if user-agent is python requests
    headers = {
        "user-agent" : "PostmanRuntime/7.37.3"
    }

    airlines = {}

    # go through the N-Numbers and determine the registration information
    i = 0
    for nnumber in flights:
        print(f"{i}: {nnumber}")
        i += 1
        payload = {
            "NNumbertxt" : nnumber
        }

        session = requests.session()

        # use get first because this page uses cookies
        response = session.get(get_url, headers=headers)
        response = session.post(post_url, headers=headers, data=payload)

        # next we'll sift through the html to find what we need:
        soup = BeautifulSoup(response.text, 'html.parser')
        owner = get_owner(soup)
        airlines[nnumber] = owner

    return airlines

    

# looks through the html soup to find the registered owner
def get_owner(soup):
    owners = []
    elements = soup.find_all('td')
    for item in elements:
        try:
            if item['data-label'] == 'Name':
                owners.append(item.get_text().strip())
        except:
            continue

    return owners

# prints the columns in an excel file
def test_print_df_cols(df):
    i = 0
    print("cols:")
    for col in df.columns:
        print(f"{i}: {col}")
        i += 1

if __name__ == '__main__':
    main()