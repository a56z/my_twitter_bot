# bot_v4.py

import os
import tweepy
import openai
import time
import logging
import random
import sqlite3
from datetime import datetime, timedelta, date
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

# Database setup
DB_NAME = 'twitter_bot.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS followed_users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            followed_at TEXT,
            thanked BOOLEAN DEFAULT 0
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS daily_follow_stats (
            date TEXT PRIMARY KEY,
            users_followed INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def create_twitter_client():
    try:
        # Initialize the Twitter client using OAuth 1.0a User Context
        client = tweepy.Client(
            consumer_key=TWITTER_API_KEY,
            consumer_secret=TWITTER_API_SECRET,
            access_token=TWITTER_ACCESS_TOKEN,
            access_token_secret=TWITTER_ACCESS_TOKEN_SECRET,
            wait_on_rate_limit=True
        )
        logging.info("Twitter API client authentication successful.")
        return client
    except Exception as e:
        logging.error("Error during Twitter API authentication", exc_info=True)
        raise e

def generate_tweet(retries=3):
    for attempt in range(retries):
        try:
            include_hashtags = random.randint(1, 5) == 5  # 1 in 5 chance to include hashtags
            prompt = (
                "Write a casual and engaging tweet about anti-aging and healthy living. "
                "Keep it friendly, use everyday language, and keep the tweet under 280 characters."
            )
            if include_hashtags:
                prompt += " Include relevant hashtags like #AntiAging #Wellness."
            else:
                prompt += " Do not include any hashtags."
            response = openai.ChatCompletion.create(
                model='gpt-4',
                messages=[
                    {"role": "system", "content": "You are a wellness enthusiast from the US East Coast who shares casual, engaging anti-aging tips on Twitter."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=80,
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
            response = client.create_tweet(text=tweet)
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
    next_start_time = current_time_est.replace(hour=8, minute=0, second=0, microsecond=0)
    if current_time_est.hour >= 8:
        next_start_time += timedelta(days=1)
    seconds_until_next_start = (next_start_time - current_time_est).total_seconds()
    return seconds_until_next_start

def get_users_followed_today():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    today_str = date.today().isoformat()
    c.execute('SELECT users_followed FROM daily_follow_stats WHERE date = ?', (today_str,))
    result = c.fetchone()
    conn.close()
    if result:
        return result[0]
    else:
        return 0

def update_users_followed_today(count):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    today_str = date.today().isoformat()
    c.execute('INSERT OR IGNORE INTO daily_follow_stats (date, users_followed) VALUES (?, 0)', (today_str,))
    c.execute('UPDATE daily_follow_stats SET users_followed = users_followed + ? WHERE date = ?', (count, today_str))
    conn.commit()
    conn.close()

def reset_daily_follow_stats():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    yesterday_str = (date.today() - timedelta(days=1)).isoformat()
    c.execute('DELETE FROM daily_follow_stats WHERE date < ?', (date.today().isoformat(),))
    conn.commit()
    conn.close()

def search_and_follow_users(client, max_users_to_follow):
    query = "anti-aging OR wellness OR healthy living -is:retweet lang:en"
    try:
        users_followed_today = get_users_followed_today()
        users_followed = 0
        remaining_follows = max(0, max_users_to_follow - users_followed_today)
        if remaining_follows <= 0:
            logging.info("Daily follow limit reached.")
            return
        # Search for recent tweets matching the query
        tweets = client.search_recent_tweets(query=query, max_results=50, tweet_fields=['author_id'])
        if tweets.data:
            for tweet in tweets.data:
                author_id = tweet.author_id
                # Check if already following or already followed recently
                if is_user_already_followed(author_id):
                    continue
                # Follow the user
                client.follow_user(target_user_id=author_id)
                logging.info(f"Followed user ID {author_id}")
                # Add to database
                add_followed_user(author_id)
                users_followed += 1
                if users_followed >= remaining_follows:
                    break
            # Update the daily follow count
            update_users_followed_today(users_followed)
        else:
            logging.info("No users found to follow.")
    except Exception as e:
        logging.error("Error during search and follow users.", exc_info=True)

def is_user_already_followed(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT 1 FROM followed_users WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    return result is not None

def add_followed_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    followed_at = datetime.utcnow().isoformat()
    c.execute('INSERT OR IGNORE INTO followed_users (user_id, followed_at) VALUES (?, ?)',
              (user_id, followed_at))
    conn.commit()
    conn.close()

def check_follow_backs_and_unfollow(client):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT user_id, followed_at, thanked FROM followed_users')
    rows = c.fetchall()
    for row in rows:
        user_id, followed_at_str, thanked = row
        followed_at = datetime.fromisoformat(followed_at_str)
        time_since_followed = datetime.utcnow() - followed_at
        try:
            # Check if the user follows back
            follows_back = client.get_user(id=user_id, user_auth=True).data.following
            if follows_back:
                logging.info(f"User ID {user_id} followed back.")
                if not thanked:
                    # Send thank-you tweet
                    send_thank_you_tweet(client, user_id)
                    # Update database
                    c.execute('UPDATE followed_users SET thanked = 1 WHERE user_id = ?', (user_id,))
                    conn.commit()
            else:
                if time_since_followed.total_seconds() > 48 * 3600:
                    # Unfollow the user
                    client.unfollow_user(target_user_id=user_id)
                    logging.info(f"Unfollowed user ID {user_id} after 48 hours of no follow-back.")
                    # Remove from database
                    c.execute('DELETE FROM followed_users WHERE user_id = ?', (user_id,))
                    conn.commit()
        except Exception as e:
            logging.error(f"Error checking follow-back status for user ID {user_id}", exc_info=True)
    conn.close()

def send_thank_you_tweet(client, user_id):
    thank_you_messages = [
        f"Thanks for the follow! 😊 Stay tuned for more anti-aging tips!",
        f"Appreciate the follow! Let's embark on this wellness journey together! 🌟",
        f"Glad to connect with you! Here's to healthy living! 🥑",
    ]
    message = random.choice(thank_you_messages)
    # Mention the user in the tweet
    message = f"@{get_username(client, user_id)} {message}"
    try:
        response = client.create_tweet(text=message)
        logging.info(f"Sent thank-you tweet to user ID {user_id}. Response: {response}")
    except Exception as e:
        logging.error(f"Error sending thank-you tweet to user ID {user_id}", exc_info=True)

def get_username(client, user_id):
    try:
        user = client.get_user(id=user_id)
        if user.data:
            return user.data.username
    except Exception as e:
        logging.error(f"Error fetching username for user ID {user_id}", exc_info=True)
    return "there"

def main():
    init_db()
    reset_daily_follow_stats()
    twitter_client = create_twitter_client()
    dry_run = False  # Set to True for testing without posting
    while True:
        if is_within_posting_hours():
            # Generate and post tweet
            tweet = generate_tweet()
            if tweet and is_content_appropriate(tweet):
                post_tweet(twitter_client, tweet, dry_run=dry_run)
            else:
                logging.warning("Generated tweet is inappropriate or empty. Skipping.")
            # Randomly decide whether to search and follow users today
            if random.choice([True, False]):
                max_users_to_follow = random.randint(1, 5)
                search_and_follow_users(twitter_client, max_users_to_follow=max_users_to_follow)
            # Check for follow-backs and unfollow if necessary
            check_follow_backs_and_unfollow(twitter_client)
            interval = random.randint(TWEET_INTERVAL_MIN, TWEET_INTERVAL_MAX)
            logging.info(f"Waiting for {interval} seconds before next tweet.")
            time.sleep(interval)
        else:
            seconds_until_next_start = calculate_seconds_until_next_window()
            logging.info("Outside of posting hours. Waiting until next posting window.")
            time.sleep(seconds_until_next_start)

if __name__ == "__main__":
    main()

