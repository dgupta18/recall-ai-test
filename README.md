# Recall AI translation testing

## Setup

1. `python3 -m venv venv`
2. `source venv/bin/activate`
3. `pip3 install flask requests dotenv svix openai`
4. Create an ngrok tunnel to your local server where the app will be running, and copy that URL to your `.env` file as WEBHOOK_BASE_URL (see ngrok section below for help)
5. Create a recall API token in the recall dashboard, and copy the token to your `.env` file as RECALL_API_TOKEN
6. Create a recall webhook in the recall dashboard here - https://us-west-2.recall.ai/dashboard/webhooks - using the ngrok url as your webhook url, and copy the signing key to your `.env` file as RECALL_WEBHOOK_SIGNING_SECRET

### .env

Now your .env should look like this:

```
RECALL_API_TOKEN=<token>
RECALL_WEBHOOK_SIGNING_SECRET=<secret>
WEBHOOK_BASE_URL=<url>
```

## Running

### Application

`python3 app.py`

### ngrok tunnel

`ngrok http 8080 #(or whichever port)`

Once you run this locally just keep it running so that the webhook endpoint doesn't need to be continually updated.

You can visit the created webhooks in your Recall Dashboard here:
https://us-west-2.recall.ai/dashboard/webhooks
