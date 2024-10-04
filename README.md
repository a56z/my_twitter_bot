## Prerequisites

- Python 3.7+
- Twitter Developer account for API keys
- OpenAI API key for generating tweets

## Installation

1. **Clone the repository**:

    ```bash
    git clone https://github.com/your-username/my_twitter_bot.git
    cd my_twitter_bot
    ```

2. Create a virtual environment (optional but recommended):

    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3. Install dependencies:

    ```bash
    pip install -r requirements.txt
    ```

4. Configure your API keys:

    Create a file named `config.py` and add the following content:

    ```python
    TWITTER_API_KEY = 'your-twitter-api-key'
    TWITTER_API_SECRET = 'your-twitter-api-secret'
    TWITTER_ACCESS_TOKEN = 'your-twitter-access-token'
    TWITTER_ACCESS_TOKEN_SECRET = 'your-twitter-access-token-secret'
    OPENAI_API_KEY = 'your-openai-api-key'

    TWEET_INTERVAL_MIN = 3600  # Minimum interval in seconds (e.g., 1 hour)
    TWEET_INTERVAL_MAX = 7200  # Maximum interval in seconds (e.g., 2 hours)
    ```

5. **Run the bot**:

    To run the bot in the background:

    ```bash
    nohup python3 bot.py > bot_output.log 2>&1 &
    ```

    You can check the bot's output with:

    ```bash
    tail -f bot_output.log
    ```

## Features

- Automatically generates tweets using the OpenAI API.
- Tweets at random intervals within a specified range.
- Logs errors and skips inappropriate or empty tweets.

## License

This project is licensed under the MIT License.

