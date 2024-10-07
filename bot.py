# bot.py

import os
import tweepy
import openai
import time
import logging
import random
from config import (
    TWITTER_OAUTH_CLIENT_ID,
    TWITTER_OAUTH_CLIENT_SECRET,
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
        auth = tweepy.OAuth1UserHandler(
            TWITTER_API_KEY,
            TWITTER_API_SECRET,
            TWITTER_ACCESS_TOKEN,
            TWITTER_ACCESS_TOKEN_SECRET
        )
        client = tweepy.API(auth)
        client.verify_credentials() 
        logging.info("Twitter API v1.1 client authentication successful.")
        return client
    except Exception as e:
        logging.error("Error during Twitter API authentication", exc_info=True)
        raise e

def generate_tweet(retries=3):
    for attempt in range(retries):
        try:
            prompt = (
                "Compose a friendly and knowledgeable tweet about anti-aging tips focusing on healthy living. "
                "Use a conversational tone, include relevant hashtags like #AntiAging #Wellness, and keep the tweet under 280 characters."
            )
            response = openai.ChatCompletion.create(
                model= 'gpt-4o-mini', #'gpt-3.5-turbo'
                messages=[
                    {"role": "system", "content": "You are a wellness enthusiast from the US East Coast who shares anti-aging tips on Twitter."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=80,  # Adjust as needed
                temperature=0.7,
                n=1,
            )
            # Extract the generated tweet
            tweet = response['choices'][0]['message']['content'].strip()
            # Ensure tweet is within Twitter's character limit
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
    # Implement content filtering logic if necessary
    return True

def post_tweet(client, tweet, dry_run=False):
    if dry_run:
        print(f"Dry run - Tweet content: {tweet}")
        logging.info("Dry run - Tweet not posted.")
    else:
        try:
            client.update_status(tweet)  # OAuth 1.0a endpoint for posting a tweet
            logging.info("Tweet posted successfully.")
        except tweepy.TweepyException as e:
            logging.error(f"Tweepy error occurred: {e}", exc_info=True)
        except Exception as e:
            logging.error("An unexpected error occurred while posting the tweet.", exc_info=True)


def main():
    twitter_client = create_twitter_client()
    dry_run = False  # Set to True for testing without posting
    while True:
        tweet = generate_tweet()
        if tweet and is_content_appropriate(tweet):
            post_tweet(twitter_client, tweet, dry_run=dry_run)
        else:
            logging.warning("Generated tweet is inappropriate or empty. Skipping.")
        interval = random.randint(TWEET_INTERVAL_MIN, TWEET_INTERVAL_MAX)
        logging.info(f"Waiting for {interval} seconds before next tweet.")
        time.sleep(interval)

if __name__ == "__main__":
    main()

