import os
import pandas as pd
import requests
from bs4 import BeautifulSoup
import pickle
from nltk.sentiment import SentimentIntensityAnalyzer
from scipy import stats
import matplotlib.pyplot as plt
import numpy as np
from transformers import pipeline

def main():
    # First, let us check for results data saved as a file
    # Unfortunately, BERT takes a long time to process
    # we'll run once and save the results to file
    results_file_path = "results.pkl"
    compute = False
    try:
        results = load_results(results_file_path)
    except FileNotFoundError:
        compute = True
        print("Final Results file was not found, performing computations.")
        print("This will take a while...")

    # if there are no saved results, we must compute
    if compute:

        ##### AIRLINE INCIDENT DATA #####

        # we'll begin by pulling in a record of commercial airline incidents from the excel file
        airlines = get_airline_incident_records()
        print(f"Number of records found/retrieved: {len(airlines)}")

        # next we need to group these records by airline, place into a dictionary
        grouped_airlines = group_sort_airlines(airlines)


        ##### CUSTOMER REVIEW DATA #####

        # first, read the csv file of customer review data
        review_df = pd.read_csv("AirlineReviews.csv")

        ##### DATA COMPUTATION #####

        # Compute all data for airlines that have a minimum incident count of at least 3
        min_incidents = 3
        results = compute_airline_data(grouped_airlines, review_df, min_incidents)

        # save the results as a pickle file
        save_results(results_file_path, results)

    #### DATA ANALYSIS ####

    # print the result data
    print_results(results)

    # generate scatter plots
    print(f"\n##\n##### Correlation Calculations: #####\n##")
    min_incidents_arr = [8, 3, 10]
    for i in range(len(min_incidents_arr)):
        title = f"Correlation Min {min_incidents_arr[i]}"
        analyze_data(results, title, min_incidents_arr[i])

    
# prints a dictionary of results
def print_results(results):
    print(f"\n##\n##### AIRLINE SCORES: #####\n##")
    for airline in results:
        # print the results data for each airline
        airline_incident_scores = results[airline]['incident_scores']
        airline_review_scores = results[airline]['review_scores']

        print(f"\n{airline}:")
        print(f"\tIncident Score: {airline_incident_scores['avg']}")

        print("\tInjury level counts:")
        for level in airline_incident_scores['injury']:
            print(f"\t\t{level}: {airline_incident_scores['injury'][level]}")

        print("\tDamage level counts:")
        for level in airline_incident_scores['damage']:
            print(f"\t\t{level}: {airline_incident_scores['damage'][level]}")

        print(f"\tVADER: {airline_review_scores['vader']}")
        print(f"\tBERT: {airline_review_scores['bert']}")

        # then create a graph to visualize the injury and damage levels
        categories = ['None', 'Minor', 'Serious/Substantial', 'Fatal/Destroyed']
        injury_values = airline_incident_scores['injury'].values()
        damage_values = airline_incident_scores['damage'].values()

        x = np.arange(len(categories))
        bar_width = 0.35

        plt.bar(x - bar_width/2, injury_values, bar_width, label='Injury Levels', color='b')
        plt.bar(x + bar_width/2, damage_values, bar_width, label='Damage Levels', color='g')

        plt.xlabel('Injury/Damage Levels')
        plt.ylabel('Counts')
        plt.title(f"{airline} Injury and Damage Counts")
        plt.xticks(x, categories)
        plt.legend()

        plt.tight_layout()
        plt.show()



# compute all data for the airlines that have at least min_incidents incidents
# returns the results dictionary
def compute_airline_data(grouped_airlines, review_df, min_incidents):    
    # get the airlines with at least min_incidents and compute the average incident score for each
    airline_incident_scores = get_airline_incident_scores(grouped_airlines, min_incidents)

    # get the review records for airlines that we have a score for, then analyze them
    reviews = get_review_records(review_df, airline_incident_scores.keys())
    airline_review_scores = get_airline_review_scores(reviews)

    # set up the results dictionary
    results = {}
    
    airlines = airline_review_scores.keys()
    for airline in airlines:
        results[airline] = {}
        results[airline]['review_scores'] = airline_review_scores[airline]
        results[airline]['incident_scores'] = airline_incident_scores[airline]
        results[airline]['num_incidents'] = len(grouped_airlines[airline])

    return results

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
                 'REPUBLIC AIRWAYS INC', 'MESA AIRLINES INC']

    # iterate over the dictionary of airlines
    for nnumber in airlines:
        airline_name = airlines[nnumber][0][0]

        # first check to make sure we don't have one of the blacklisted names
        if airline_name in blacklist:
            continue

        # if we have encountered a new airline name, create a new entry in the dict
        elif airline_name not in grouped_airlines.keys():
            grouped_airlines[airline_name] = [(nnumber, airlines[nnumber])]

        # if we encounter an airline name already in the dict, update the existing listing
        else:
            grouped_airlines[airline_name].append((nnumber, airlines[nnumber]))
    
    sorted_airlines = dict(sorted(grouped_airlines.items()))

    # test print the groupings
    """ for group in sorted_airlines:
        #print(f"Name: {group}\nRecords: {sorted_airlines[group]}\n\n")
        print(f"{group} with {len(sorted_airlines[group])} records") """

    return sorted_airlines

# creates an incident score for each airline in a grouped airline dictionary
def get_airline_incident_scores(grouped_airlines, min_records):
    airline_scores = {}

    # convert the injury and damage level to a weight
    injury_rubric = {
        'None' : 1,
        'Minor' : 2,
        'Serious' : 3,
        'Fatal' : 4,
    }

    damage_rubric = {
        'None' : 1,
        'Minor' : 2,
        'Substantial' : 3,
        'Destroyed' : 4
    }

    # step through the grouped airlines dictionary and score qualifying airlines
    for airline_name in grouped_airlines:
        if len(grouped_airlines[airline_name]) >= min_records:
            # create some dictionaries to keep track of the number of occurrences of each injury/damage level
            airline_scores[airline_name] = {}
            airline_scores[airline_name]['injury'] = {
                'None': 0,
                'Minor': 0,
                'Serious': 0,
                'Fatal': 0
            }
            airline_scores[airline_name]['damage'] = {
                'None': 0,
                'Minor': 0,
                'Substantial': 0,
                'Destroyed': 0
            }

            sum = 0
            for incident_record in grouped_airlines[airline_name]:
                # get the injury and damage level
                injury = incident_record[1][1]
                damage = incident_record[1][2]

                # increment the counters for these levels
                injury_counter = airline_scores[airline_name]['injury'][injury]
                damage_counter = airline_scores[airline_name]['damage'][damage]
                airline_scores[airline_name]['injury'][injury] = injury_counter + 1
                airline_scores[airline_name]['damage'][damage] = damage_counter + 1

                # then add the incident avg to the running airline sum
                sum += (injury_rubric[injury] + damage_rubric[damage])

            avg = sum / (2 * len(grouped_airlines[airline_name])) # avg for the current airline

            airline_scores[airline_name]['avg'] = avg

    return airline_scores

# create a list of airline reviews from the excel file that are only for the airlines with a score
def get_review_records(df, airline_names):
    reviews = {}

    # important col numbers are as follows:
    # col 1: Airline name
    # col 11: Review Text that we will be using NLP to analyze
    # col 18: If the Review was verified or not
    # col 21: Review ID

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
                #review = [df.iloc[i, 21], df.iloc[i, 11], -1]
                review = [df.iloc[i, 11]] # we only really need the review text
                if name not in reviews.keys():
                    reviews[name] = [review]
                else:
                    reviews[name].append(review)

    return reviews

# analyzes the review text for a dictionary of reviews by airline
# Two different methods are used to analyze the review texts
def get_airline_review_scores(airline_reviews):
    # airline review score dict
    review_scores = {}

    ## VADER sentiment Analyzer
    ## Simpler model of the two
    sia = SentimentIntensityAnalyzer()

    ## BERT sentiment analyzer
    ## More advanced, should give better results
    # We could train BERT on our own review data, but that would require a labeling of pos, neg, or neutral
    # to already be present in the dataset
    # BERT do be slow tho...
    sentiment_pipeline = pipeline('sentiment-analysis', model='distilbert-base-uncased-finetuned-sst-2-english')    

    # iterate through each airline
    for airline in airline_reviews:
        print(f"Analyzing {len(airline_reviews[airline])} reviews for {airline}!")
        review_scores[airline] = {}

        vader_sum = 0
        bert_sum = 0
        
        # then iterate over every review for that airline
        review_list = airline_reviews[airline]
        for review in review_list:
            vader_sentiment = sia.polarity_scores(review[0])
            vader_sum += convert_vader_scale(vader_sentiment['compound'])

            # before using BERT, we have to chunk the review text
            chunks = split_into_chunks(review[0], chunk_size=300)

            # then analyze each chunk and average the sentiment scores
            for chunk in chunks:
                bert_sum += convert_bert_scale(sentiment_pipeline(chunk)[0])

        # calculate the average for the airline
        review_scores[airline]['vader'] = vader_sum / len(review_list)
        review_scores[airline]['bert'] = bert_sum / len(review_list)

    return review_scores

# converts the VADER compound score(-1 to 1) to a scale from 1 to 10
def convert_vader_scale(score):
    return round((score + 1) * 4.5 + 1)

# converts the BERT sentiment score to a scale from 1 to 10
# the sentiment is binary with a label, and the score is actually just a confidence metric
def convert_bert_scale(sentiment):
    label = sentiment['label']
    score = sentiment['score']

    if label == 'POSITIVE':
        return round(score * 5 + 5) # Map [0.5, 1.0] to [6, 10]
    else:
        return round((1 - score) * 5 + 1) # Map [0.0, 0.5] to [1, 5]

# splits text into chunks of size no bigger than max tokens
def split_into_chunks(text, chunk_size=300):
    words = text.split() # get the words from the text
    return [" ".join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]

# Checks for correlation between a list of incident scores and sentiment scores for airlines
def analyze_data(results, title, min_incidents):
    print(f"\n##### {title} #####")
    print("Airlines included: ")
    for airline in results:
        if results[airline]['num_incidents'] >= min_incidents:
            print(f"\t{airline}")

    # create a list of the airline names with at least min_incidents incidents
    airline_names = []
    for airline in results:
        if results[airline]['num_incidents'] >= min_incidents:
            airline_names.append(airline)

    # create a list of just the incident scores
    incident_scores = []
    for airline in airline_names:
        incident_scores.append(results[airline]['incident_scores']['avg'])

    # create a list of just the review scores, one for vader and another for bert
    vader_review_scores = []
    bert_review_scores = []
    for airline in airline_names:
        vader_review_scores.append(results[airline]['review_scores']['vader'])
        bert_review_scores.append(results[airline]['review_scores']['bert'])

    # perform the correlation calculations
    print("\nVADER Correlation:")
    result_spearman = stats.spearmanr(vader_review_scores, incident_scores)
    spearman_stat, spearman_pvalue = result_spearman
    print(f"\tSpearman Result: Correlation of {spearman_stat} with pvalue {spearman_pvalue}")
    #print(f"\tSpearman Result: {result_spearman}")

    result_pearson = stats.pearsonr(vader_review_scores, incident_scores)
    pearson_stat, pearson_pvalue = result_pearson
    print(f"\tPearson Result: Correlation of {pearson_stat} with pvalue {pearson_pvalue}")
    #print(f"\tPearson Result: {result_pearson}")

    # plot the graph for the vader sentiment analyzer
    plt.figure(figsize=(8, 6))
    plt.scatter(incident_scores, vader_review_scores, color='green', alpha=0.7)
    for i in range(len(airline_names)):
        plt.text(incident_scores[i], vader_review_scores[i], airline_names[i])
    plt.title(f"{title} VADER")
    plt.xlabel("Incident Score")
    plt.ylabel("Sentiment Score")
    plt.grid(True)
    plt.show()

    # perform the correlation calculations
    print("BERT Correlation")
    result_spearman = stats.spearmanr(bert_review_scores, incident_scores)
    spearman_stat, spearman_pvalue = result_spearman
    print(f"\tSpearman Result: Correlation of {spearman_stat} with pvalue {spearman_pvalue}")
    #print(f"\tSpearman Result: {result_spearman}")

    result_pearson = stats.pearsonr(bert_review_scores, incident_scores)
    pearson_stat, pearson_pvalue = result_pearson
    print(f"\tPearson Result: Correlation of {pearson_stat} with pvalue {pearson_pvalue}")
    #print(f"\tPearson Result: {result_pearson}")

    # then plot the graph for the bert sentiment analyzer
    plt.figure(figsize=(8, 6))
    plt.scatter(incident_scores, bert_review_scores, color='green', alpha=0.7)
    for i in range(len(airline_names)):
        plt.text(incident_scores[i], bert_review_scores[i], airline_names[i])
    plt.title(f"{title} BERT")
    plt.xlabel("Incident Score")
    plt.ylabel("Sentiment Score")
    plt.grid(True)
    plt.show()

# retrieves the final results dictionary from a file
def load_results(file_path):
    with open(file_path, "rb") as file:
        try:
            results = pickle.load(file)
            return results
        except:
            # some error loading the file occurred, return None
            return None

# saves the final result dictionary as a pickle object to a file
def save_results(file_path, results):
    with open(file_path, "wb") as file:
        pickle.dump(results, file)

# prints the columns in an excel file
def test_print_df_cols(df):
    i = 0
    print("cols:")
    for col in df.columns:
        print(f"{i}: {col}")
        i += 1

if __name__ == '__main__':
    main()