#!/usr/bin/env python

from tweepy.streaming import StreamListener
from tweepy import OAuthHandler
from tweepy import Stream, API
from datetime import datetime
from optparse import OptionParser
import random
import json
import time
import sys
import ConfigParser
import re
import logging
import logging.config

rdict= {'hug': '*hugs*', 'luck': 'Good luck :)',
        'sad': ['You deserve a compliment!', 'I appreciate all of your opinions.',
                'Don\'t be sad, You\'re tremendous!', 'Your smile is breath taking.',
                'I would share my fruit Gushers with you', 'You\'re sweeter than than a bucket of bon-bons!'],
        'lonely': ['You are a bucket of awesome', 'Don\'t be, I\'m here for you', 'You have the best laugh ever.'],
        'depressed': ['I hope you feel better.'], 'job':  ['You deserve a promotion.'],
        'pathetic': ['You are better than unicorns and sparkles combined!'],
        'nervous': ["Don't worry. You'll do great :)"]}
# keywords = ['I need a hug', 'I feel sad', 'I feel lonely', 'I\'m depressed', 'I hate my job', 'I am pathetic', 'I\'m nervous']
keywords = ['I need a hug', 'I\'m depressed', 'I hate my job', 'I am pathetic', 'I\'m nervous', 'Wish me luck', '@complimebot']

reply_compliments = ['You are a bucket of awesome', 'You are better than unicorns and sparkles combined!',
                     'Your smile is breath taking.', 'Your mouse told me that you have very soft hands.',
                     'I appreciate you more than Santa appreciates chimney grease.',
                     'You make my data circuits skip a beat.']

INTERVAL = 0  # First compliment should be posted immediatly
replied_type = []
r_macro = re.compile("""(?<=^|(?<=[^a-zA-Z0-9-_\.]))@([A-Za-z]+[A-Za-z0-9]+)""")
api = '' # fugly temp placeholder

FILE_CONFIG = 'compli.conf'
LOG_CONFIG = 'logging.ini'

logging.config.fileConfig(LOG_CONFIG)
logger = logging.getLogger(__name__)

### Read configs ###
parser = ConfigParser.ConfigParser()
parser.read(FILE_CONFIG)
section = "Twitter"
consumer_key = parser.get(section, "CON_KEY")
consumer_secret = parser.get(section, "CON_SEC")
access_token = parser.get(section, "ACC_KEY")
access_token_secret = parser.get(section, "ACC_SEC")
### /Read configs ###


class Tweet:
    def __init__(self, tweet):
        self.tweet = tweet
        self.text = tweet['text']
        self.id = tweet['id']
        self.name = tweet['user']['screen_name']

    def isRT(self):
        if self.tweet.get('retweeted_status'):
            return True

    def isMention(self):
        return not (self.tweet['entities']['user_mentions'] == [])

    def isURL(self):
        return not (self.tweet['entities']['urls'] == [])


class StdOutListener(StreamListener):
    """ A listener handles tweets are the received from the stream.
    This is a basic listener that just prints received tweets to stdout.

    """
    def on_data(self, data):
        data = json.loads(data)
        replyIfMention(data)
        if getDiff(lastPostTime) < INTERVAL:
            return
        process(data)
        return True

    def on_error(self, status):
        logger.debug(status)


def response(text):
    global replied_type

    if len(replied_type) == len(keywords)-1:
        replied_type[:] = []

    if 'was' in text:
        return None

    if 'hug' in text and 'hug' not in replied_type:
        replied_type.append('hug')
        return rdict['hug']
    elif 'luck' in text and 'luck' not in replied_type:
        replied_type.append('luck')
        return rdict['luck']
    # elif 'sad' in text and 'sad' not in replied_type:
    #     replied_type.append('sad')
    #     return random.choice(rdict['sad'])
    # elif 'lonely' in text and 'lonely' not in replied_type:
    #     replied_type.append('lonely')
    #     return random.choice(rdict['lonely'])
    elif 'depressed' in text and 'depressed' not in replied_type:
        replied_type.append('depressed')
        return random.choice(rdict['depressed'])
    elif 'job' in text and 'job' not in replied_type:
        replied_type.append('job')
        return random.choice(rdict['job'])
    elif 'pathetic' in text and 'pathetic' not in replied_type:
        replied_type.append('pathetic')
        return random.choice(rdict['pathetic'])
    elif 'nervous' in text and 'nervous' not in replied_type:
        replied_type.append('nervous')
        return random.choice(rdict['nervous'])


def post(tweet, reply):
    global lastPostTime
    global INTERVAL
    INTERVAL = random.randint(30, 100)
    status = '@' + tweet.name + ' ' + reply
    logger.info(status)
    logger.info("Next post in %d minutes" % INTERVAL)
    lastPostTime = getCurUTCTime()
    if not options.dry:
        api.update_status(status, tweet.id)


def replyIfMention(data):  # refactor this shiz
    tweet = Tweet(data)
    text = tweet.text.lower()
    if text[0:12] == '@complimebot' and 'need' in text:
        other_mentions = r_macro.findall(text)
        users = ' @'.join(other_mentions)
        users = users.replace('complimebot', '')
        if 'compliment' in text:
            status = '@' + tweet.name + users + ' ' + random.choice(reply_compliments)
        elif 'hug' in text:
            status = '@' + tweet.name + users + ' ' + rdict['hug']
        logger.info('Mention> %s' % text)
        logger.info('Reply> %s' % status)
        if not options.dry:
            api.update_status(status, tweet.id)


def process(data):
    tweet = Tweet(data)
    if not (tweet.isRT() or tweet.isMention() or tweet.isURL()):
        logger.info(tweet.text)
        reply = response(tweet.text.lower())
        if reply:
            post(tweet, reply)


def getCurUTCTime():
    return datetime.utcnow()


def getDiff(dtime):
    delta = getCurUTCTime() - dtime
    return (delta.days * 86400 + delta.seconds) / 60


def main():
    try:
        global api
        logger.info("Authorizing with Twitter")
        l = StdOutListener()
        auth = OAuthHandler(consumer_key, consumer_secret)
        auth.set_access_token(access_token, access_token_secret)
        logger.info("Authorized Twitter")
        api = API(auth)

        stream = Stream(auth, l)
        stream.filter(track=keywords)

    except Exception, e:
        logger.debug('%s, %s ' % (sys.exc_traceback.tb_lineno, e))


### Parse command-line args ###
parser = OptionParser()
parser.add_option("-d", "--dryrun", action="store_true", dest="dry", default=False, help="If specified, no posts will be made")

(options, args) = parser.parse_args()
### /Parse command-line args ###

lastPostTime = getCurUTCTime()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.debug("Terminating...")
