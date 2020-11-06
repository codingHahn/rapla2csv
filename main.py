import re
import requests
import csv
import dateconvert
import datetime
import argparse
from bs4 import BeautifulSoup
from lesson import Lesson
from timeobj import Time


def weekdays_to_index(weekday):
    if weekday == "Mo":
        return 0
    if weekday == "Di":
        return 1
    if weekday == "Mi":
        return 2
    if weekday == "Do":
        return 3
    if weekday == "Fr":
        return 4
    if weekday == "Sa":
        return 5
    # If there is now weekday, just dump it into Saturday,
    # but log it. Most likely a date blocked by exam placeholders
    print('Exam-placeholder in week {}'.format(current_date.isocalendar()[1]))
    return -1


PARSER = argparse.ArgumentParser(description='Rapla to csv converter')
PARSER.add_argument('link', metavar='Link', type=str,
                    help='Link where to fetch from')
PARSER.add_argument('from_', metavar='From', type=str,
                    help='Beginning date')
PARSER.add_argument('to', metavar='To', type=str,
                    help='End date')
PARSER.add_argument('-o', '--outputfile', metavar='file', type=str, nargs='?',
                    help='Name of the output csv file')

args = PARSER.parse_args()

url = args.link
current_date = datetime.datetime.fromisoformat(args.from_)
end_date = datetime.datetime.fromisoformat(args.to)

# Variables, that will be needed over multiple scrapes
params = dict()
lessons = list() # Ultimate list of all lesson objects that got scraped

# Repeat scraping for every week in the desired timeframe
while current_date <= end_date:
    # Put the wanted month and day into the url params
    params['month'] = current_date.month
    params['day'] = current_date.day
    params['year'] = current_date.year
    
    r = requests.get(url, params=params)

    soup = BeautifulSoup(r.content.decode(), 'lxml')

    # Replace all <br> elements with newlines for easier
    # text manipulation down the line
    for br in soup.find_all('br'):
        br.replace_with('\n')

    # The year has to be read from the dropdown menu, because it is
    # written nowhere else on the page. The server preselects an item
    # in the 'year' dropdown menu. This is the year the user is currently
    # viewing
    year = soup.find('select', attrs={'name': 'year'}).find_all('option')
    for y in year:
        if y.has_attr('selected'):
            year = y.text
            break

    # The dates of the week that is loaded get extracted here
    # They get put into a list with the weekday stripped.
    # The first item in the list is the date for Monday,
    # the second for Tuesday etc.
    d = soup.find_all('td', class_='week_header')
    dates = list()
    for i in d:
        dates.append(dateconvert.rapladate_to_iso(
            "{}{}".format(i.text.split(' ')[1], year)))

    s = soup.find_all('td', class_='week_block')
    for i in s:
        lesson = Lesson()

        # Instructor:
        # Rapla sends the instructor as "name,surname,".
        # To make this pretty, we switch both parts and remove
        # both commas
        person = i.find('span', class_='person')
        
        # If there is now person, it is an exam
        if person:
            person = person.text.split(',')
            lesson.instructor = "{} {}".format(
                person[1].strip(), person[0].strip())
        else:
            print('The week {} contains exams'.format(current_date.isocalendar()[1]))
            person = "Klausur"

        # Start and Endtime
        timeobj = Time()
        time = i.find('a').text.split('\n')[0].split('-')
        time = list(map(lambda x: x.strip(), time))
        timeobj.start_time = time[0]
        timeobj.end_time = time[1]

        # Date:
        # In the lessons themselves the only date information saved
        # is of the weekday. To get the corresponding date we have
        # to lookup in the dates list mentioned above
        weekday = i.find('span', class_='tooltip').find_all(
            'div')[1].text.split(' ', maxsplit=1)[0].strip()
        w = weekdays_to_index(weekday)
        # Is the extracted Information a weekday?
        if w >= 0 and w <= 5:
            timeobj.date = dates[w]
            lesson.date = timeobj
        else:
            # If there is no information about when the event is,
            # just drop the whole event
            print("Could not find weekday information. Special handling now")
            tds = i.parent.find_all('td')
            count = 1

            # TODO: Cleanup
            # When we are here, we haven't gotten any useful weekday information
            # yet. Here we count, how many days passed before we encounter
            # the current lesson. This should work
            for t in tds:
                if t['class'][0] == 'week_emptycell_black' or t['class'][0] == 'week_block':
                    if t['class'][0] == 'week_block':
                        if t == i:
                            break
                    count += 1

            if count >= 0 and count <= 5:
                timeobj.date = dates[count]
                lesson.date = timeobj
            else:
                break

        # Room
        # Online: When the class is held online, that is reflected in the
        # lessons name. This gets cut out here and pasted into the room field
        # Non-Online: The Room is extracted from its proper place
        name = i.find('a').text.split('\n')[1].split('erstellt am')[0]
        if re.search("^Online", name):
            name = name.split('-', maxsplit=1)[1].strip()
            room = "Online"
        else:
            room = i.find('span', class_='tooltip').find('strong').text

        lesson.name = name
        lesson.room = room
        lessons.append(lesson)

    # At the end of the main loop, increment the date by 7 days
    current_date += datetime.timedelta(7)

if args.outputfile == None:
    args.outputfile = 'csvfile.csv'

with open(args.outputfile, 'w') as csvfile:
    # Write a header so that the file can be undestood by humans
    csvfile.write(
        "Subject,Start Date,Start Time,End Date,End Time,Description,Location\n")
    WRITER = csv.writer(csvfile, delimiter=',', lineterminator="\n",
                        quotechar='"', quoting=csv.QUOTE_MINIMAL)
    # All lessons are saved in the 'lessons' list,
    # through iterating through them, all lessons get saved
    for i in lessons:
        WRITER.writerow([i.name, i.date.date, i.date.start_time,
                         i.date.date, i.date.end_time, i.instructor, i.room])
