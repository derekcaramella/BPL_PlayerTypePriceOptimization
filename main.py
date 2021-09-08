# Import necessary modules
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
import time
from bs4 import BeautifulSoup
import requests
import ast
import re
import pandas as pd
import openpyxl

file = open('prem_year_urls.txt', 'r')  # Open text file as read only
contents = file.read()  # Read the open file
prem_year_urls_dictionary = ast.literal_eval(contents)  # Read file into a dictionary, txt file is in the same format
file.close()  # Close the file

# Location of chrome drive for selenium
path = r'C:\Users\derek\AppData\Roaming\JetBrains\PyCharmCE2021.2\scratches\chromedriver.exe'
options = Options()  # Options class that enables options in the drive
options.headless = True  # Headless makes the chrome window not open
driver = webdriver.Chrome(path, options=options)  # Create the driver

# (Match ID, Match Date, Season, Attendance, Match Home Team, Match Away Team, Home Goals, Away Goals)
match_result_list = []  # An empty list to populate the dataframe
# (Match ID, Home/Away, Formation, Possession, Shots on Target, Shots, Touches, Passes, Tackles, Clearances, Corners,
# Offsides, Yellow Cards, Red Cards, Fouls Conceded)
match_team_stats_list = []  # An empty list to populate the dataframe

driver.get('https://www.premierleague.com')  # Navigate to webpage
driver.find_element_by_xpath('/html/body/section/div/div').click()  # Click to permit cookies
time.sleep(2)  # Sleep two seconds to load page

for season in prem_year_urls_dictionary.keys():  # For each season in the dictionary
    season_value = prem_year_urls_dictionary[season]
    print(season_value)
    r = requests.get(season)  # Get the season with requests
    soup = BeautifulSoup(r.content, 'html.parser')  # Read the requests into beautiful soup
    splice_soup = soup.find('div', {'class': 'wrapper col-12 tabLoader u-hide'})  # A Div that has all match ids & stuff
    splice_soup_delimited = str(splice_soup).split('"')  # Split the match id string by " to remove some stuff
    data_fixture_id_bool = False  # A boolean that switches on when data-fixturesids is seen
    match_ids = ''  # An ending string for match ids, we will split by commas later
    for i in splice_soup_delimited:  # For each element in data-fixturesids
        if data_fixture_id_bool is True:  # If the switch is on
            match_ids = i  # This string contains all match ids split by a comma
            data_fixture_id_bool = False  # Turn the switch off
        if i == ' data-fixturesids=':  # If the string is  data-fixturesids= turn the switch on
            data_fixture_id_bool = True  # Turn the switch on
    match_ids = match_ids.split(',')  # Split match ids by comma

    for match_id in match_ids:  # For each match id in the season
        print('https://www.premierleague.com/match/' + match_id)
        driver.get('https://www.premierleague.com/match/' + match_id)  # Navigate to match id webpage
        time.sleep(2)  # Sleep two seconds

        fixture_date = driver.find_element_by_xpath(
            r'//*[@id="mainContent"]/div/section[2]/div[2]/section/div[1]/div/div[1]/div[1]').text  # Fixture Date
        attendance = driver.find_element_by_xpath(
            r'//*[@id="mainContent"]/div/section[2]/div[2]/section/div[3]/div/div/div[2]/div[2]').text  # Attendance

        # Navigate to line-up tab
        driver.find_element_by_xpath(
            r'//*[@id="mainContent"]/div/section[2]/div[2]/div[2]/div[1]/div/div/ul/li[2]').click()
        time.sleep(2)  # Sleep two seconds
        # Home Formation text
        home_formation = driver.find_element_by_xpath(
            r'//*[@id="mainContent"]/div/section[2]/div[2]/div[2]/div[2]/section[2]/div/div/div[1]/div/header/div/strong').text
        # Away Formation text
        away_formation = driver.find_element_by_xpath(
            r'//*[@id="mainContent"]/div/section[2]/div[2]/div[2]/div[2]/section[2]/div/div/div[3]/div/header/div/strong').text

        # Move to Stats tab
        driver.find_element_by_xpath(
            r'//*[@id="mainContent"]/div/section[2]/div[2]/div[2]/div[1]/div/div/ul/li[3]').click()
        time.sleep(4)
        # Use explict wait time because there is a lot of data
        try:
            # Wait for div to become visible then continue, this contains all the data
            stat_list = WebDriverWait(driver, 10).until(ec.visibility_of_element_located((By.XPATH, r'//*[@id="mainContent"]/div/section[2]/div[2]/div[2]/div[2]/section[3]/div[2]/div[2]')))
            stat_list = stat_list.text.split('\n')  # Split by each new line, [home stat category away stat]
        except:  # If could not load div
            driver.quit()  # Quit driver

        home_team = stat_list[1].replace('  ', '')  # Get home team name, replace extra spaces with nothing
        away_team = stat_list[2]  # Get away team name
        home_goal = driver.find_element_by_xpath(
            r'//*[@id="mainContent"]/div/section[2]/div[2]/section/div[3]/div/div/div[1]/div[2]/div/div').text.split(
            '-')[0]  # Home goals. Split the div based on hyphen (-), then first element
        away_goal = driver.find_element_by_xpath(
            r'//*[@id="mainContent"]/div/section[2]/div[2]/section/div[3]/div/div/div[1]/div[2]/div/div').text.split(
            '-')[1]  # Away goals. Split the div based on hyphen (-), then first element
        # Record for math result dataframe
        match_result_list.append((match_id, season, fixture_date, attendance,
                                  home_team, away_team, home_goal, away_goal))

        # Staged record for home & away stats
        home_stats = (match_id, 'Home', home_formation, home_team,)
        away_stats = (match_id, 'Away', away_formation, away_team,)

        for stat in stat_list[3:]:  # For each stat in the stats excluding the top three (match stats, home, away)
            if '.' in stat:  # If a decimal is in the stat
                # Split & float, first instance is home
                home_stat = [float(x) for x in re.findall(r"-?\d+\.\d+", stat)][0]
                # Split & float, first instance is away
                away_stat = [float(x) for x in re.findall(r"-?\d+\.\d+", stat)][1]
            else:
                home_stat = re.split(r'(\d+)', stat)[1]  # Second instance is home
                away_stat = re.split(r'(\d+)', stat)[3]  # Fourth instance is away
            home_stats = home_stats + (home_stat,)  # Add onto instance home record
            away_stats = away_stats + (away_stat,)  # Add onto instance away record


        driver.find_element_by_xpath(
            r'//*[@id="mainContent"]/div/section[2]/div[2]/div[2]/div[2]/section[3]/div[1]/ul/ul/li[1]').click()
        time.sleep(2)
        season_so_far = driver.find_element_by_xpath(r'//*[@id="mainContent"]/div/section[2]/div[2]/div[2]/div[2]/section[3]/div[2]/div[1]/div[2]/section').text.split('\n')

        for stat in season_so_far[3:]:  # For each stat in the stats excluding the top three (match stats, home, away)
            print(stat)
            if 'Position' in stat or 'Avg Goals Scored Per Match' in stat or 'Avg Goals Conceded Per Match' in stat or 'Chances Created Per Match' in stat:  # If a decimal is in the stat
                if '.' in stat:  # If a decimal is in the stat
                    try:
                        # Split & float, first instance is home
                        home_stat = [float(x) for x in re.findall(r"-?\d+\.\d+", stat)][0]
                        # Split & float, first instance is away
                        away_stat = [float(x) for x in re.findall(r"-?\d+\.\d+", stat)][1]
                    except IndexError:
                        home_stat = re.split(r'(\d+)', stat)[1]  # Second instance is home
                        away_stat = re.split(r'(\d+)', stat)[3]  # Fourth instance is away
                else:
                    home_stat = re.split(r'(\d+)', stat)[1]  # Second instance is home
                    away_stat = re.split(r'(\d+)', stat)[3]  # Fourth instance is away

                home_stats = home_stats + (home_stat,)  # Add onto instance home record
                away_stats = away_stats + (away_stat,)  # Add onto instance away record

        print(home_stats)
        match_team_stats_list.append(home_stats)  # Append record
        match_team_stats_list.append(away_stats)  # Append record

# Create dataframe
match_result_df = pd.DataFrame(match_result_list, columns=['Match ID', 'Season', 'Match Date', 'Attendance',
                                                           'Home Team', 'Away Team', 'Home Goals', 'Away Goals'])
# Create dataframe
match_team_stats_df = pd.DataFrame(match_team_stats_list, columns=['Match ID', 'Home/Away', 'Formation', 'Team',
                                                                   'Possession', 'Shots on Target', 'Shots', 'Touches',
                                                                   'Passes', 'Tackles', 'Clearances', 'Corners',
                                                                   'Offsides', 'Yellow Cards', 'Red Cards',
                                                                   'Fouls Conceded', 'Current League Position',
                                                                   'Current Average Goals per Match',
                                                                   'Current Average Goals Conceded Per Match',
                                                                   'Current Chances Created Per Match'])

match_result_df.to_excel('Match Results.xlsx', index=False)  # Export dataframe
match_team_stats_df.to_excel('Team Stats.xlsx', index=False)  # Export dataframe
