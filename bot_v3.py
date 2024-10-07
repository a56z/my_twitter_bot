# bot_v3.py

import os
import tweepy
import openai
import time
import logging
import random
from datetime import datetime, timedelta
import pytz  # To handle timezone conversions
from config import (
    TWITTER_API_KEY,
    TWITTER_API_SECRET,
    TWITTER_ACCESS_TOKEN,
    TWITTER_ACCESS_TOKEN_SECRET,
    OPENAI_API_KEY,
    TWEET_INTERVAL_MIN,
    TWEET_INTERVAL_MAX
)

# Configure logging
logging.basicConfig(
    filename='logs/bot.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Initialize OpenAI API
openai.api_key = OPENAI_API_KEY

def create_twitter_client():
    try:
        # Initialize the Twitter client using OAuth 1.0a User Context
        client = tweepy.Client(
            consumer_key=TWITTER_API_KEY,
            consumer_secret=TWITTER_API_SECRET,
            access_token=TWITTER_ACCESS_TOKEN,
            access_token_secret=TWITTER_ACCESS_TOKEN_SECRET
        )
        logging.info("Twitter API client authentication successful.")
        return client
    except Exception as e:
        logging.error("Error during Twitter API authentication", exc_info=True)
        raise e

def generate_tweet(retries=3):
    for attempt in range(retries):
        try:
            prompt = (
                "Write a casual and engaging tweet about anti-aging and healthy living. "
                "Keep it friendly, use everyday language, and include relevant hashtags like #AntiAging #Wellness. "
                "Avoid using quotation marks at the beginning and end. Keep the tweet under 280 characters."
            )
            response = openai.ChatCompletion.create(
                model='gpt-4',  # Or 'gpt-3.5-turbo' if you don't have access to gpt-4
                messages=[
                    {"role": "system", "content": "You are a wellness enthusiast from the US East Coast who shares casual, engaging anti-aging tips on Twitter."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=80,  # Adjust as needed
                temperature=0.8,
                n=1,
            )
            tweet = response['choices'][0]['message']['content'].strip()
            # Remove leading and trailing quotation marks, if any
            tweet = tweet.strip('\"\'')
            if len(tweet) > 280:
                tweet = tweet[:277] + '...'
            logging.info(f"Generated tweet: {tweet}")
            return tweet
        except openai.error.OpenAIError as e:
            logging.error(f"OpenAI API error on attempt {attempt + 1}: {e}", exc_info=True)
            time.sleep(2)
        except Exception as e:
            logging.error(f"Unexpected error on attempt {attempt + 1}: {e}", exc_info=True)
            time.sleep(2)
    return None

def is_content_appropriate(tweet):
    # For now, all generated tweets are considered appropriate
    return True

def post_tweet(client, tweet, dry_run=False):
    if dry_run:
        print(f"Dry run - Tweet content: {tweet}")
        logging.info("Dry run - Tweet not posted.")
    else:
        try:
            response = client.create_tweet(text=tweet)  # Posting tweet using v2 endpoint
            logging.info(f"Tweet posted successfully. Response: {response}")
        except tweepy.TweepyException as e:
            logging.error(f"Tweepy error occurred: {e}", exc_info=True)
        except Exception as e:
            logging.error("An unexpected error occurred while posting the tweet.", exc_info=True)

def is_within_posting_hours():
    # Define the posting window in EST
    est = pytz.timezone('US/Eastern')
    current_time_est = datetime.now(est)
    start_time = current_time_est.replace(hour=8, minute=0, second=0, microsecond=0)
    end_time = current_time_est.replace(hour=22, minute=0, second=0, microsecond=0)
    if start_time <= current_time_est <= end_time:
        return True
    else:
        return False

def calculate_seconds_until_next_window():
    est = pytz.timezone('US/Eastern')
    current_time_est = datetime.now(est)
    next_start_time = current_time_est.replace(hour=8, minute=0, second=0, microsecond=0) + timedelta(days=1)
    seconds_until_next_start = (next_start_time - current_time_est).total_seconds()
    return seconds_until_next_start

def main():
    twitter_client = create_twitter_client()
    dry_run = False  # Set to True for testing without posting
    while True:
        if is_within_posting_hours():
            tweet = generate_tweet()
            if tweet and is_content_appropriate(tweet):
                post_tweet(twitter_client, tweet, dry_run=dry_run)
            else:
                logging.warning("Generated tweet is inappropriate or empty. Skipping.")
            interval = random.randint(TWEET_INTERVAL_MIN, TWEET_INTERVAL_MAX)
            logging.info(f"Waiting for {interval} seconds before next tweet.")
            time.sleep(interval)
        else:
            seconds_until_next_start = calculate_seconds_until_next_window()
            logging.info("Outside of posting hours. Waiting until next posting window.")
            time.sleep(seconds_until_next_start)

if __name__ == "__main__":
    main()

