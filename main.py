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
    incidents = get_incident_records(accident_df)
    print(f"Found {len(incidents)} commercial flights")

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
        # query the user to read the current file or refetch from the web page
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

    # user requested to load the present file
    if not query:
        with open(file_path, "rb") as file:
            try:
                airlines = pickle.load(file)
            except:
                # just in case of a file error, we'll go ahead and refetch the data
                print("Error reading the file, new data needs to be fetched")
                query = True

        # test print the loaded registration data
        if not query:
            i = 0
            for nnumber in airlines.keys():
                print(f"{i}: ({nnumber}: {airlines[nnumber]})")
                i += 1

    # user requested, or forced, to fetch the registration data
    if query:
        print("Fetching registration info . . .")
        with open(file_path, "wb") as file:
            airlines = get_registration(incidents)
            pickle.dump(airlines, file)

    # make some pretty graphs using numpy or something




# create a list of just part 121 flights from a df
def get_incident_records(df):
    incidents = []

    # check every record for its aviation type
    for i in range(len(df)):
        if '121' in df.iloc[i, 17]:
            # append the n-number[0], highest injury level[1], damage level[2], and the event date[3]
            incidents.append([df.iloc[i, 13], df.iloc[i, 10], df.iloc[i, 12], df.iloc[i, 2]])

    return incidents

# get registration information
def get_registration(incidents):
    get_url = 'https://registry.faa.gov/aircraftinquiry/Search/NNumberInquiry'
    post_url = 'https://registry.faa.gov/aircraftinquiry/Search/NNumberResult'

    # will not work if user-agent is python requests
    headers = {
        "user-agent" : "PostmanRuntime/7.37.3"
    }

    # this is the dict that will hold the record of incident information
    airlines = {}

    # go through the N-Numbers and determine the registration information
    i = 0
    for incident in incidents:
        # set the nnumber as the payload for the POST request
        payload = {
            "NNumbertxt" : incident[0]
        }

        session = requests.session()

        # use get first because this page uses cookies
        response = session.get(get_url, headers=headers)
        response = session.post(post_url, headers=headers, data=payload)

        # parse the html and save a copy
        soup = BeautifulSoup(response.text, 'html.parser')
        owner = get_owner(soup, incident)
        if len(owner) != 0:
            # if an owner was found, add it to the dict along with other incident info
            airlines[incident[0]] = owner
            print(f"{i}: ({incident[0]}: {airlines[incident[0]]})")
            
        else:
            print(f"{i}: ({incident[0]}: ###NO OWNER FOUND###)")

        i += 1

    return airlines

# looks through the html soup to find the registered owner
def get_owner(soup, incident):
    records = []

    # extract the date of the incident to make sure we grab the correct record from the
    # faa website
    inc_date = incident[3]
    inc_year = inc_date.year
    inc_month = inc_date.month
    inc_day = inc_date.day
    
    # everything we need is under the main div
    main_div = soup.find('div', id='mainDiv')

    # next we'll get the table wrapping divs that fall underneath the main div
    # all the data we'll need are in these tables
    div_tables = []
    divs = main_div.find_all('div')
    for div in divs:
        if 'devkit-simple-table-wrapper' in div.attrs.get('class', []):
            div_tables.append(div)

    #reserved = 'Reserved N-Number'
    deregistered = 'Deregistered Aircraft'
    assigned = 'Aircraft Description'
    owner = 'Registered Owner'

    # go through each of the found data tables
    possible_owners = {}
    for div in div_tables:

        # if the n-number is assigned, then it will have an owner caption
        # if the n-numuber has deregistered entries, then it will have a deregistered caption
        captions = div.find_all('caption')
        for caption in captions:
            issue_date = exp_date = 'NOT FOUND'

            caption_text = caption.get_text().strip()
            if caption_text == assigned: # this caption will be present if the n-number is assigned

                # grab the registration date
                td_elements = div.find_all('td')
                for td in td_elements:
                    try:
                        # grab the issue date and the expiration date
                        if td['data-label'] == 'Certificate Issue Date':
                            issue_date = td.get_text().strip()
                        elif td['data-label'] == 'Expiration Date':
                            exp_date = td.get_text().strip()
                    except:
                        continue

            elif caption_text == owner: # this caption will also be present if the n-number is assigned

                # grab the current owner information
                td_elements = div.find_all('td')
                for td in td_elements:
                    try:
                        # check every td that has a data-label of 'Name'
                        if td['data-label'] == 'Name':
                            name = td.get_text().strip()
                            if name != 'CANCELLED/NOT ASSIGNED' and name != 'SALE REPORTED' and name != 'None':
                                possible_owners[name] = {'ISSUE':issue_date, 'CANCEL':exp_date}
                    except:
                        continue

            elif caption_text == deregistered: # true if the n-number has deregistered records

                # for each deregistered owner, check the date against the incident date
                found_issue = found_cancel = False

                td_elements = div.find_all('td')
                for td in td_elements:
                    if td['data-label']:
                        # look for certificate issue and cancel dates, and the owner
                        if td['data-label'] == 'Certificate Issue Date':
                            issue_date = td.get_text().strip()
                            found_issue = True

                        elif td['data-label'] == 'Cancel Date':
                            cancel_date = td.get_text().strip()
                            found_cancel = True

                        elif td['data-label'] == 'Name':
                            # since the owner is the last record to appear, we'll add what we have to the dict
                            if found_issue and found_cancel:
                                deregistered_owner = td.get_text().strip()
                                possible_owners[deregistered_owner] = {'ISSUE':issue_date, 'CANCEL':cancel_date}
                                issue_date = cancel_date = False
                            else:
                                print('An owner was found out of order...')
                        
            else:
                # we found a table that doesn't match any of the above
                print(f"Caption: {caption_text}")

            # now that we have a dict of all the deregistered owners, find the correct one, if any
            keys = possible_owners.keys()
            for possible_owner in keys:
                date_dict = possible_owners[possible_owners]

    num = denom = 1
    header = f"DeregisteredAircraft{num}of{denom}"
    
    return records

# prints the columns in an excel file
def test_print_df_cols(df):
    i = 0
    print("cols:")
    for col in df.columns:
        print(f"{i}: {col}")
        i += 1

if __name__ == '__main__':
    main()