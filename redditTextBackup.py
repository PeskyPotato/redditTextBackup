import argparse

'''
Parses input
'''
parser = argparse.ArgumentParser(description="Command line tool for archiving text posts on Reddit")
parser.add_argument("SubReddit", help="Enter a sub reddit to archive text from")
parser.add_argument("--time", help="Time to schedule archives, default is 11am")

args = parser.parse_args()

subR = None
filepath = None
if '.txt' in args.SubReddit:
    filepath = args.SubReddit   #Sets filepath to input text file of subreddits
else:
    subR = args.SubReddit       #If no file passed in

if args.time:
    timeS = args.time
else:
    timeS = '11:00'             #Default time if no time is specified



import praw
import json

'''
Creates instance of reddit from config.json
'''
with open('config.json') as json_file:
    config = json.load(json_file)

reddit = praw.Reddit(client_id = config['client_id'],
                     client_secret= config['client_secret'],
                     user_agent= config['user_agent'],
                     username = config['username'],
                     password = config['password'])

import datetime
import re
import time
import os
import sys
from prawcore.exceptions import RequestException
from prawcore.exceptions import Redirect
import schedule

'''
Creats texts files from submission
'''
def backup(subR, startTime, endTime):
    try:
        for submission in reddit.subreddit(subR).submissions(startTime, endTime):           #Takes the submission within time frame
            title = submission.title
            date = datetime.datetime.utcfromtimestamp(submission.created_utc)
            author = submission.author

            writeLog('{} {}'.format(title.encode('utf-8'), date))


            if not os.path.exists(os.path.join(subR)):                                      #Makes a folder with Subreddits name
                os.makedirs(subR)

            #Makes a txt file with date, title and author of submission in the above folder
            fileName = '{} - {} - {}.txt'.format(formatName(str(date)), formatName(str(title)), formatName(str(author)))
            f = open(os.path.join(subR, fileName), 'a', encoding = 'utf-8')

            f.write('{} - {}{}'.format('Title', title, '\n'))
            f.write('{} - {}{}'.format('Date', date, '\n'))
            f.write('{} - {}{}'.format('Author', author, '\n'))
            toWrite = submission.selftext
            f.write(str(toWrite)+'\n')

            f.write("\n##########  Comments:  ##########\n")    #Writes comments three levels deep
            try:                                                #To catch "AttributeError: 'MoreComments' object has no attribute 'author'" not sure why

                for comment in submission.comments:
                    f.write('User: {} - {}\n'.format(str(comment.author),str(comment.body)))
                    for reply in comment.replies:
                        f.write('{}User: {} - {}\n'.format('    ', str(reply.author), str(reply.body)))
                        for reply0 in reply.replies:
                            f.write('{}User: {} - {}\n'.format('        ', str(reply0.author), str(reply0.body)))
                            for reply1 in reply0.replies:
                                f.write('{}User: {} - {}\n'.format('            ', str(reply1.author), str(reply1.body)))
            except AttributeError:
                writeLog('Attribute Error encountered, skipping comment section for {}'.format(submission))

            f.close()
    except Redirect:
        writeLog('Invalid subreddit "{}"'.format(subR))
        return

'''
Removes invalid characters and shortens file names if too long
'''
def formatName(title):
    title = re.sub('[?/|\\\:<>*"]', '', title)
    if len(title) > 170:
        title = title[:90]
    return title

'''
Writes to log file, takes in string
'''
def writeLog(st):
    print(st)
    fLog = open('{}-log.txt.'.format(subR), 'a')
    fLog.write('{}: {}\n'.format(str(datetime.datetime.utcnow()), st))
    fLog.close()

'''
Handles dates and calls backup
'''
def main():
    curUTC = datetime.datetime.utcnow()
    curUNIX = time.mktime(curUTC.timetuple())

    if not os.path.isfile('{}-timestamps.txt'.format(subR)):
        startUNIX = curUNIX -  34560000     #Start date is a year before current date
        endUNIX = curUNIX - 604800          #End date is 7 days before the current date
    else:
        with open('{}-timestamps.txt'.format(subR)) as fTime:
            lines = fTime.read().splitlines()
        startUNIX = float(lines [1])        #Start date if previously archived is the previous end date
        endUNIX = float(startUNIX + 86400)  #End date is the start date plus 1 day
        fTime.close()

    out = '****Archiving from {} to {} on {}****'.format(str(datetime.datetime.utcfromtimestamp(startUNIX)),str(datetime.datetime.utcfromtimestamp(endUNIX)), subR)
    writeLog(out)
    backup(subR, startUNIX, endUNIX)

    #After backup is complete new date and time is written to file
    fTime = open('{}-timestamps.txt'.format(subR), 'w')
    fTime.write('{}\n{}'.format(str(startUNIX), str(endUNIX)))
    fTime.close()

    out = '{} UTC: Waiting...'.format(str(datetime.datetime.utcnow()))
    writeLog(out)

'''
Feeds subreddit to main
'''
def driver():
    if filepath is not None:
        with open(filepath) as fileP:
            line = fileP.readline()
            while line:
                global subR
                subR = "{}".format(line.strip())
                main()
                line = fileP.readline()
    else:
        main()


if __name__ == '__main__':
    writeLog('Starting intial archive...')

    driver()

    schedule.every().day.at(timeS).do(driver)

    while True:
        try:
            schedule.run_pending()
        except RequestException:
            writeLog('Request timed out retrying...')
            time.sleep(10)
            schedule.run_pending()
        time.sleep(10)
