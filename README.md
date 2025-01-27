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

 If you decide to run the calculations yourself, you'll need to grab the updated customer review dataset from [kaggle](https://www.kaggle.com/datasets/joelljungstrom/128k-airline-reviews). Make sure it saves as 'AirlineReviews.csv'. You are now ready to run the program and perform the calculations!