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
    print("Reading accident data . . .")
    accident_df = pd.read_excel("AviationAccidentStatistics_2003-2022_20231228.xlsx", sheet_name=28)

    # now we'll create a list of N-Numbers from part 121 airlines from the accident data
    flights = get_commercial_flights(accident_df)
    print(f"Found {len(flights)} commercial flights")

    # next we'll read the csv file of customer review data
    # col 1: Airline name
    # col 5: If the review is verified
    # col 6: Review text we will be analyzing (the core of the project)
    print("Reading review data . . .")
    review_df = pd.read_csv("Airline_review.csv")

    print("Checking for registration data . . .")
    file_path = "registration_info.pkl"
    if not os.path.exists(file_path):
        # file does not exist, we need to query the web page
        query = True
    else:
        # determine whether to read the current file or refetch from the web page
        while True:
            user_input = input("A registration info file exists: Read file instead of fetching data? (y/n): ")
            if user_input == 'y':
                query = False
                break
            elif user_input == 'n':
                query = True
                break
            else:
                print("Please input either y or n")

    if not query:
        with open(file_path, "rb") as file:
            try:
                airlines = pickle.load(file)
            except:
                print("Error reading the file, new data needs to be fetched")
                query = True

        # test print of the registration data
        i = 0
        for nnumber in airlines.keys():
            print(f"{i}: ({nnumber}: {airlines[nnumber]})")
            i += 1

    if query:
        print("Fetching registration info . . .")
        with open(file_path, "wb") as file:
            airlines = get_registration(flights)
            pickle.dump(airlines, file)

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
        if len(owner) != 0:
            airlines[nnumber] = owner
            print(f"{i}: ({nnumber}: {airlines[nnumber]})")
            
        else:
            print(f"{i}: ({nnumber}: ###NO OWNER FOUND###)")

        i += 1

    return airlines

    

# looks through the html soup to find the registered owner
def get_owner(soup):
    owners = []
    elements = soup.find_all('td')
    for item in elements:
        try:
            if item['data-label'] == 'Name' or item['data-label'] == 'Reserving Party Name':
                name = item.get_text().strip()
                if name == 'CANCELLED/NOT ASSIGNED' or name == 'SALE REPORTED' or name == 'None':
                    continue
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