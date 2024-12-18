#import scrapy
import pandas as pd
import numpy

# read the airline accident data from the excel file, we want sheet 29 from the file
df = pd.read_excel("AviationAccidentStatistics_2003-2022_20231228.xlsx", sheet_name=28)

# important columns (from zero index)
# 13: Registration Number (to get carrier)
# 17: Flight Regulation (commercial, private, charter, etc)



#print(df.head())
print(df)

i = 1
print("cols:")
for col in df.columns:
    print(f"{i}: {col}")
    i += 1

# need to scrape the review data and store into some easily usable format


# then make the comparison between the two data sets

# make some pretty graphs using numpy or something