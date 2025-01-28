# Airline Safety as it Relates to Customer Reviews

## Required Packages
 - os
 - pandas
 - requests
 - bs4
 - pickle
 - nltk
 - scipy
 - matplotlib
 - numpy
 - transformers
 
 ## Running
 If you're running the program from a directoy cloned from git, you shouldn't need to run the time-consuming calculations. The final results are stored in results.pkl and as long as you have this file, you can avoid the calculations and therefore the requirement of needing the other data files. If you want to run the calculations again, just delete the results.pkl file and it will recreate it automatically. 

 If you decide to run the calculations yourself, you'll need to grab the updated customer review dataset from the review data link below. Make sure it saves as 'AirlineReviews.csv'. You are now ready to run the program and perform the calculations!

 ### Note
 The program will execute inside the .org file and generate the graphs, but the printed output will not write inside of the file. To see the graphs and the printed output, execute main.py with python.

 ## Links
 Here are some links to the datasets that I used and some information on the VADER and BERT tools for sentiment analysis.

 [Incident Data](https://www.ntsb.gov/safety/Pages/research.aspx)

 [Review Data](https://www.kaggle.com/datasets/joelljungstrom/128k-airline-reviews)

 [FAA N-Number Search](https://registry.faa.gov/aircraftinquiry/Search/NNumberInquiry)

 [VADER](https://www.geeksforgeeks.org/python-sentiment-analysis-using-vader/)

 [BERT](https://www.geeksforgeeks.org/sentiment-classification-using-bert/)