import os
import pandas as pd
import requests
from bs4 import BeautifulSoup
import pickle
from nltk.sentiment import SentimentIntensityAnalyzer
from scipy import stats
import matplotlib.pyplot as plt

def main():
    ##### AIRLINE INCIDENT DATA #####

    # we'll begin by pulling in a record of airline incidents
    airlines = get_airline_incident_records()
    print(f"Number of records found/retrieved: {len(airlines)}")

    # next we need to group these records by airline
    grouped_airlines = group_sort_airlines(airlines) 


    ##### CUSTOMER REVIEW DATA #####

    # first, read the csv file of customer review data
    # col 1: Airline name
    # col 11: Review Text that we will be using NLP to analyze
    # col 18: If the Review was verified or not
    # col 21: Review ID
    review_df = pd.read_csv("AirlineReviews.csv")


    ##### DATA ANALYSIS #####

    ##
    ## TEST 1, minimum incidents required = 8 ##
    ##
    title = "Correlation Min 8"

    # get the airlines with at least 8 incidents and compute average incident score for each
    airline_scores = score_airlines(grouped_airlines, 8)

    # get the review records for airlines that we have a score for, then analyze them
    reviews = get_review_records(review_df, airline_scores.keys())
    analyze_reviews(reviews)

    print("\nAverage incident scores:")
    for airline in airline_scores:
        print(f"{airline}: {airline_scores[airline]}")

    print("\nAverage sentiments:")
    for airline in reviews:
        print(f"{airline}: {reviews[airline][1]}")

    analyze_data(airline_scores, reviews, title)

    ##
    ## TEST 2, minimum incidents required = 3 ##
    ##
    title = "Correlation Min 3"

    # get the airlines with at least 8 incidents and compute average incident score for each
    airline_scores = score_airlines(grouped_airlines, 3)

    # get the review records for airlines that we have a score for, then analyze them
    reviews = get_review_records(review_df, airline_scores.keys())
    analyze_reviews(reviews)

    print("\nAverage incident scores:")
    for airline in airline_scores:
        print(f"{airline}: {airline_scores[airline]}")

    print("\nAverage sentiments:")
    for airline in reviews:
        print(f"{airline}: {reviews[airline][1]}")

    analyze_data(airline_scores, reviews, title)

    ##
    ## TEST 3, minimum incidents required = 10 ##
    ##
    title = "Correlation Min 10"

    # get the airlines with at least 8 incidents and compute average incident score for each
    airline_scores = score_airlines(grouped_airlines, 10)

    # get the review records for airlines that we have a score for, then analyze them
    reviews = get_review_records(review_df, airline_scores.keys())
    analyze_reviews(reviews)

    print("\nAverage incident scores:")
    for airline in airline_scores:
        print(f"{airline}: {airline_scores[airline]}")

    print("\nAverage sentiments:")
    for airline in reviews:
        print(f"{airline}: {reviews[airline][1]}")

    analyze_data(airline_scores, reviews, title)


# takes user prompt to either load incident records from file(if exists) or fetch from the web
def get_airline_incident_records():
    print("Checking for registration data . . .")
    file_path = "registration_info.pkl"
    if not os.path.exists(file_path):
        # file does not exist, we need to query the web page
        query = True
    else:
        # query the user to read the current file or refetch from the web page
        """ while True:
            user_input = input("A registration info file exists: Read file instead of fetching data? (y/n): ")
            if user_input == 'y':
                query = False
                break
            elif user_input == 'n':
                query = True
                break
            else:
                print("Please input either y or n") """
        query = False

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
        """ if not query:
            i = 0
            for nnumber in airlines.keys():
                print(f"{i}: ({nnumber}: {airlines[nnumber]})")
                i += 1 """

    # user requested, or forced, to fetch the registration data
    if query:
        # read the airline accident data from the excel file, we want sheet 29 from the file
        # col 13: Registration Number (to get airline carrier)
        # col 17: Flight Regulation (commercial, private, charter, etc; we are looking for commercial)
        print("Reading accident data . . .")
        accident_df = pd.read_excel("AviationAccidentStatistics_2003-2022_20231228.xlsx", sheet_name=28)

        # now we'll create a list of N-Numbers from part 121 airlines from the accident data
        incidents = get_commercial_flights(accident_df)
        print(f"Found {len(incidents)} commercial flights")

        print("Fetching registration info . . .")
        with open(file_path, "wb") as file:
            airlines = get_registration(incidents)
            pickle.dump(airlines, file)

    return airlines

# create a list of just part 121 flights from a df
def get_commercial_flights(df):
    incidents = []

    # pull only the part 121 flights from the dataframe
    for i in range(len(df)):
        if '121' in df.iloc[i, 17]:
            # append the n-number[0], highest injury level[1], damage level[2], and the event date[3]
            incidents.append([df.iloc[i, 13], df.iloc[i, 10], df.iloc[i, 12], df.iloc[i, 2]])

    # we need to replace the NaN values, this poses a problem for airline scoring later
    df['Highest Injury Level'] = df['Highest Injury Level'].fillna('None')
    df['Damage Level'] = df['Damage Level'].fillna('None')

    return incidents

# get registration information for a set of incident records
def get_registration(incidents):
    get_url = 'https://registry.faa.gov/aircraftinquiry/Search/NNumberInquiry'
    post_url = 'https://registry.faa.gov/aircraftinquiry/Search/NNumberResult'

    # will not work if user-agent is python requests
    headers = {
        "user-agent" : "PostmanRuntime/7.37.3"
    }

    # this is the dict that will hold the record of incident information
    # n-numbers are the keys
    airlines = {}

    # go through the N-Numbers and determine the registration information
    i = 0
    for incident in incidents:
        # set the nnumber as the payload for the POST request
        payload = {
            "NNumbertxt" : incident[0]
        }

        session = requests.session()

        # use GET first because this page uses cookies
        response = session.get(get_url, headers=headers)
        response = session.post(post_url, headers=headers, data=payload)

        # parse the html and save a copy
        soup = BeautifulSoup(response.text, 'html.parser')

        # next we'll find the owner during the time of the incident
        owner = get_owner_information(soup, incident)
        if len(owner) != 0:
            # if an owner was found, add it to the dict along with injury and damage info
            airlines[incident[0]] = (owner, incident[1], incident[2])
            print(f"{i}: ({incident[0]} on {incident[3]}: {airlines[incident[0]]})\n")
            
        else:
            print(f"{i}: ({incident[0]} on {incident[3]}: ###NO OWNER FOUND###)\n")

        i += 1

    return airlines

# looks through the html soup to find the registered owner
def get_owner_information(soup, incident):
    # extract the date of the incident to make sure we grab the correct record from the faa website
    inc_date = incident[3]
    inc_year = inc_date.year
    inc_month = inc_date.month
    inc_day = inc_date.day
    
    # everything we need is under the main div
    main_div = soup.find('div', id='mainDiv')

    # next we'll get the table wrapping divs that fall underneath the main div
    div_tables = []
    divs = main_div.find_all('div')
    for div in divs:
        if 'devkit-simple-table-wrapper' in div.attrs.get('class', []):
            div_tables.append(div)

    # these are the captions that describe the tables that we want to look for
    deregistered = 'Deregistered Aircraft'
    assigned = 'Aircraft Description'
    owner = 'Registered Owner'

    # extract every possible owner from these div tables
    issue_date = exp_date = 'NOT FOUND'
    possible_owners = {}
    for div in div_tables:
        # if the n-number is assigned, then it will have an owner caption
        # if the n-numuber has deregistered entries, then it will have a deregistered caption

        # pull the captions that are under the current div
        captions = div.find_all('caption')
        for caption in captions:
            caption_text = caption.get_text().strip()

            ##### This segment gets the listed owner under the current registration, if it exists #####
            if caption_text == assigned: # this caption will be present if the n-number is assigned
                
                # grab the registration date
                td_elements = div.find_all('td')
                for td in td_elements:
                    if td['data-label']:
                        # grab the issue date and the expiration date
                        if td['data-label'] == 'Certificate Issue Date':
                            if td.get_text().strip() != 'None':
                                issue_date = td.get_text().strip()
                            else:
                                issue_date = 'NOT FOUND'
                        elif td['data-label'] == 'Expiration Date':
                            if td.get_text().strip() != 'None':
                                exp_date = td.get_text().strip()
                            else:
                                exp_date = 'NOT FOUND'

            elif caption_text == owner: # this caption will also be present if the n-number is assigned
                
                # grab the current owner information
                td_elements = div.find_all('td')
                for td in td_elements:
                    if td['data-label']:
                        # check every td that has a data-label of 'Name'
                        if td['data-label'] == 'Name':
                            name = td.get_text().strip()
                            if name != 'CANCELLED/NOT ASSIGNED' and name != 'SALE REPORTED' and name != 'None':
                                possible_owners[name] = {'ISSUE':issue_date, 'CANCEL':exp_date}

            ##### This segment gets the listed owner(s) that have been deregistered #####
            elif caption_text == deregistered: # true if the n-number has deregistered records

                # for each deregistered owner, check the date against the incident date
                found_issue = found_cancel = False
                issue_date = exp_date = 'NOT FOUND'

                td_elements = div.find_all('td')
                for td in td_elements:
                    if td['data-label']:
                        # look for certificate issue and cancel dates, and the owner
                        if td['data-label'] == 'Certificate Issue Date':
                            if td.get_text().strip() != 'None':
                                issue_date = td.get_text().strip()
                            else:
                                issue_date = 'NOT FOUND'
                            found_issue = True

                        elif td['data-label'] == 'Cancel Date':
                            if td.get_text().strip() != 'None':
                                cancel_date = td.get_text().strip()
                            else:
                                cancel_date = 'NOT FOUND'
                            found_cancel = True

                        elif td['data-label'] == 'Name':
                            # since the owner is the last record to appear, we'll add what we have to the dict
                            if found_issue and found_cancel:
                                deregistered_owner = td.get_text().strip()
                                if deregistered_owner != 'CANCELLED/NOT ASSIGNED' and deregistered_owner != 'SALE REPORTED' and deregistered_owner != 'None':
                                    possible_owners[deregistered_owner] = {'ISSUE':issue_date, 'CANCEL':cancel_date}
                                found_issue = found_cancel = False
                            else:
                                print('An owner was found out of order...')

    # now that we have a dict of all the deregistered owners, find the correct one, if any
    keys = possible_owners.keys()
    for possible_owner in keys:
        date_dict = possible_owners[possible_owner]

        # the dates are of the form mm/dd/yyyy
        #print(f"ISSUE: {date_dict['ISSUE']}; CANCEL: {date_dict['CANCEL']}")
        if date_dict['ISSUE'] != 'NOT FOUND' and date_dict['CANCEL'] != 'NOT FOUND':
            str_issue_month, str_issue_day, str_issue_year = date_dict['ISSUE'].split('/', 2)
            str_exp_month, str_exp_day, str_exp_year = date_dict['CANCEL'].split('/', 2)
        else:
            # we could not find the dates for the current entry, we can't use it
            continue

        issue_month, issue_day, issue_year = int(str_issue_month), int(str_issue_day), int(str_issue_year)
        exp_month, exp_day, exp_year = int(str_exp_month), int(str_exp_day), int(str_exp_year)

        # the date of the incident must be between the issue and cancel dates
        if inc_year > issue_year and inc_year < exp_year:
            # The incident is within the correct range, this is the correct owner
            return [possible_owner, possible_owners[possible_owner]]
                
        # if the incident and the issue date have the same year
        elif inc_year == issue_year:
            if inc_month > issue_month:
                # the incident is within the correct range, this is the correct owner
                return [possible_owner, possible_owners[possible_owner]]
                    
            # if the incident and the issue dates have the same month and year
            elif inc_month == issue_month:
                if inc_day >= issue_day:
                    return [possible_owner, possible_owners[possible_owner]]

        # if the incident and the expiration date have the same year
        elif inc_year == exp_year: 
            if inc_month < exp_month:
                # the incident is wihin the correct range, this is the correct owner
                return [possible_owner, possible_owners[possible_owner]]
                    
            # if the incident and the expiration dates have the same month and year
            elif inc_month == exp_month:
                if inc_day >= exp_day:
                    return [possible_owner, possible_owners[possible_owner]]
                        
    # if we make it out of the for loop without returning, none of the entries matched the date
    #print(f"NO OWNER FOUND, PRINTING POSSIBLE OWNERS DICTIONARY:\n{possible_owners}\n")

    return {}

# takes a dictionary of airline records and groups them by airline
# returns a dictionary consisting of each airline and the records for those airlines
def group_sort_airlines(airlines):
    grouped_airlines = {}

    # these are all cargo/other airlines, except for Republic and Mesa which oddly have no data in the review set
    blacklist = ['FEDERAL EXPRESS CORP', 'FEDERAL EXPRESS CORPORATION', 'UNITED PARCEL SERVICE CO',
                 'WELLS FARGO BANK NA TRUSTEE', 'WELLS FARGO BANK NORTHWEST NA TRUSTEE',
                 'WELLS FARGO TRUST CO NA TRUSTEE', 'WILMINGTON TRUST CO TRUSTEE', 'BANK OF UTAH TRUSTEE',
                 'REPUBLIC AIRWAYS INC', 'MESA AIRLINES INC'
                 ]

    # iterate over the dictionary of airlines
    for airline in airlines:
        # first check to make sure we don't have one of the blacklisted names
        if airlines[airline][0][0] in blacklist:
            continue

        # if we have encountered a new airline name, create a new entry in the dict
        elif airlines[airline][0][0] not in grouped_airlines.keys():
            grouped_airlines[airlines[airline][0][0]] = [(airline, airlines[airline])]

        # if we encounter an airline name already in the dict, update the existing listing
        else:
            grouped_airlines[airlines[airline][0][0]].append((airline, airlines[airline]))
    
    sorted_airlines = dict(sorted(grouped_airlines.items()))

    # test print the groupings
    """ for group in sorted_airlines:
        #print(f"Name: {group}\nRecords: {sorted_airlines[group]}\n\n")
        print(f"{group} with {len(sorted_airlines[group])} records") """

    return sorted_airlines

# creates an incident score for each airline in a grouped airline dictionary
def score_airlines(grouped_airlines, min_records):
    airline_scores = {}

    # convert the injury and damage level to a weight
    rubric = {
        'None' : 1,
        'Minor' : 2,
        'Serious' : 3,
        'Substantial' : 3,
        'Fatal' : 4,
        'Destroyed' : 4
    }

    # step through the grouped airlines dictionary and score qualifying airlines
    for airline_name in grouped_airlines:
        if len(grouped_airlines[airline_name]) >= min_records:
            # we have a qualifying airline, perform the weighted scoring
            sum = 0
            for incident_record in grouped_airlines[airline_name]:
                sum += (rubric[incident_record[1][1]] + rubric[incident_record[1][2]])

            avg = sum / (2 * len(grouped_airlines[airline_name]))

            #airline_scores.append((airline_name, avg))
            airline_scores[airline_name] = avg

    return airline_scores

# create a list of airline reviews that are only for the airlines with a score
def get_review_records(df, airline_names):
    reviews = {}

    # replace the NaN values in the text field, these reviews need to be left out
    df['Review'] = df['Review'].fillna('NO TEXT')

    # iterate through every review in the df
    for i in range(len(df)):
        # if the text field has 'NO TEXT', skip it
        if df.iloc[i, 11] == 'NO TEXT':
            continue

        # check if the airline name matches one we have a score for
        for name in airline_names:
            if df.iloc[i, 1].upper() in name:
                # we have a match! add the review record to the dict
                # reviews[name] = [[id, review text, sentiment placeholder], avg]
                review = [df.iloc[i, 21], df.iloc[i, 11], -1]
                if name not in reviews.keys():
                    reviews[name] = [[review], 0]
                else:
                    reviews[name][0].append(review)

    return reviews

# analyzes the review text for a dictionary of reviews by airline
def analyze_reviews(airline_reviews):
    # initialize the sentiment intensity analyzer
    sia = SentimentIntensityAnalyzer()

    # iterate through each airline
    for airline in airline_reviews:
        #print(f"Analyzing sentiment for {airline}!")
        sum = 0
        
        # then iterate over every review for that airline
        review_list = airline_reviews[airline][0]
        for review in review_list:
            sentiment = sia.polarity_scores(review[1])
            review[2] = convert_scale(sentiment['compound'])
            sum += review[2]

        # calculate the average for the airline
        airline_reviews[airline][1] = sum / len(review_list)

# converts the VADER compound score(-1 to 1) to a scale from 1 to 10
def convert_scale(compound_score):
    return round((compound_score + 1) * 4.5 + 1)

# Checks for correlation between a list of incident scores and sentiment scores for airlines
def analyze_data(airline_scores, reviews, title):
    incident_scores = []
    names = []
    for airline in airline_scores:
        incident_scores.append(airline_scores[airline])
        names.append(airline)
    review_scores = []
    for airline in reviews:
        review_scores.append(reviews[airline][1])

    plt.figure(figsize=(8, 6))
    plt.scatter(incident_scores, review_scores, color='green', alpha=0.7)
    for i in range(len(names)):
        plt.text(incident_scores[i], review_scores[i], names[i])
    plt.title(title)
    plt.xlabel("Incident Score")
    plt.ylabel("Sentiment Score")
    plt.grid(True)
    plt.show()

    result_spearman = stats.spearmanr(review_scores, incident_scores)
    print(f"Spearman Result: {result_spearman}")

    result_pearson = stats.pearsonr(review_scores, incident_scores)
    print(f"Pearson Result: {result_pearson}")

# prints the columns in an excel file
def test_print_df_cols(df):
    i = 0
    print("cols:")
    for col in df.columns:
        print(f"{i}: {col}")
        i += 1

if __name__ == '__main__':
    main()