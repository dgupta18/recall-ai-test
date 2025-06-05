# Recall AI translation testing

## Setup

1. `python3 -m venv venv`
2. `source venv/bin/activate`
3. `pip3 install flask requests dotenv svix`
4. Create a webhook https://us-west-2.recall.ai/dashboard/webhooks and copy the signing key to a `.env` file
5. Create a recall API token and copy the token to the `.env` file

### .env

Now your .env should look like this:

```
RECALL_API_TOKEN=<token>
RECALL_WEBHOOK_SIGNING_SECRET=<secret>
```

## Running

### Application

`python3 app.py`

### ngrok tunnel

`ngrok http 8080 #(or whichever port)`

Once you run this locally just keep it running so that the webhook endpoint doesn't need to be continually updated.

You can visit the created webhooks in your Recall Dashboard here:
https://us-west-2.recall.ai/dashboard/webhooks