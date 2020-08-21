import re, requests, time, sys
import csv
import dateconvert
import datetime
from bs4 import BeautifulSoup
from lesson import Lesson
from timeobj import Time
import argparse


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

parser = argparse.ArgumentParser(description='Rapla to csv converter')
parser.add_argument('link', metavar='Link', type=str,
                    help='Link where to fetch from')
parser.add_argument('from_', metavar='From', type=str, nargs='?',
                    help='Beginning date')
parser.add_argument('to', metavar='To', type=str, nargs='?',
                    help='End date')

args = parser.parse_args()

params = dict()
lessons = list()
url = args.link
print(args)
current_date = datetime.datetime.fromisoformat(args.from_)
end_date = datetime.datetime.fromisoformat(args.to)
while current_date <= end_date:
    params['month'] = current_date.month
    params['day'] = current_date.day
    print(current_date)
    current_date += datetime.timedelta(7)
    r = requests.get(url, params=params)
    print(r.status_code)

    soup = BeautifulSoup(r.content.decode(), 'lxml')

    for br in soup.find_all('br'):
        br.replace_with('\n')


#TODO: Do for all dates in range
    year = soup.find('select', attrs={'name' : 'year'}).find_all('option')
    for y in year:
        if y.has_attr('selected'):
            year = y.text
            break

    d = soup.find_all('td', class_='week_header')
    dates = list()
    for i in d:
        dates.append(dateconvert.rapladate_to_iso("{}{}".format(i.text.split(' ')[1], year)))
    s = soup.find_all('td', class_='week_block')

    for i in s:
        lesson = Lesson()
        # Instructor
        person = i.find('span', class_='person').text.split(',')
        lesson.instructor = "{} {}".format(person[1].strip(), person[0].strip())

        # Start and Endtime
        timeobj = Time()
        time = i.find('a').text.split('\n')[0].split('-')
        time = list(map(lambda x: x.strip(), time))
        timeobj.start_time = time[0]
        timeobj.end_time = time[1]

        # Date
        weekday = i.find('span', class_='tooltip').find_all('div')[1].text.split(' ', maxsplit=1)[0].strip()
        timeobj.date = dates[weekdays_to_index(weekday)]
        lesson.date = timeobj

        # Room
        name = i.find('a').text.split('\n')[1].split('erstellt am')[0]
        if re.search("^Online", name):
            name = name.split('-', maxsplit=1)[1].strip()
            lesson.name = name
            room = "Online"
            lesson.room = room
        else:
            pass
        #print(name)
        lessons.append(lesson)
        #print(lesson.__dict__)
        #print(timeobj.__dict__)
    
with open('csvfile.csv', 'w') as csvfile:
    csvfile.write("Subject,Start Date,Start Time,End Date,End Time,Description,Location\n")
    writer = csv.writer(csvfile, delimiter=',', lineterminator="\n",
                            quotechar='"', quoting=csv.QUOTE_MINIMAL)
    for i in lessons:
        writer.writerow([i.name, i.date.date, i.date.start_time, i.date.date, i.date.end_time, i.instructor, i.room])
