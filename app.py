import os
import logging
import requests
from openai import AzureOpenAI
from dotenv import load_dotenv
from flask import Flask, request, jsonify, Response, send_file
# from svix.webhooks import Webhook, WebhookVerificationError

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
load_dotenv()
RECALL_API_TOKEN = os.getenv('RECALL_API_TOKEN')
RECALL_WEBHOOK_SIGNING_SECRET = os.getenv('RECALL_WEBHOOK_SIGNING_SECRET')
AZURE_OPENAI_API_KEY = os.getenv('AZURE_OPENAI_API_KEY')
RECALL_BASE_URL = os.getenv('RECALL_BASE_URL', 'https://us-east-1.recall.ai/api/v1/bot')
WEBHOOK_BASE_URL = os.getenv('WEBHOOK_BASE_URL', 'http://localhost:8080')
USING_PROVIDER = False

def translate_text(text):
    # Configuration
    endpoint = "https://innovation-hub.openai.azure.com/"
    model_name = "gpt-4o"

    api_version = "2024-12-01-preview"
    try:
        client = AzureOpenAI(
            api_version=api_version,
            azure_endpoint=endpoint,
            api_key=AZURE_OPENAI_API_KEY,
        )
        logger.info("Azure OpenAI client initialized successfully.")
    except Exception as e:
        logger.error("Failed to initialize Azure OpenAI client.")
        logger.error(e)
        # Raise the exception instead of using exit
        raise e
    try:
        # Use the client to translate text
        response = client.chat.completions.create(
            model=model_name,
            temperature=0,
            messages=[
                {
                    'role': 'user',
                    'content': f"""
                    [text]
                        {text}
                    [/text]
                    [task]
                        Translate the text to SPANISH.
                        The text is in "US-EN".
                        Ensure that the translation is accurate and maintains the original meaning.
                    [/task]
                    [response criteria]
                        - The translation should be clear and concise.
                        - Any mistakes in the original text should be corrected.
                        - The response should be in English and PLAINTEXT format. DO NOT WRAP THE RESPONSE IN ANY MARKUP.
                        - RESPOND ONLY WITH PLAINTEXT TRANSLATED TEXT. IMPORTANT!
                        - Do not include any additional information or explanations.
                        - Do not include any other text or formatting.
                    [/response criteria]

                    DO NOT INCLUDE THINGS LIKE: `Here is the translation of the provided text:`!
                    DO NOT INCLUDE THINGS LIKE: `The translation is as follows:`!
                    DO NOT INCLUDE THINGS LIKE: `The translated text is:`!
                    DO NOT INCLUDE THINGS LIKE: `The translation is:`!
                    ONLY PROVIDE THE TRANSLATION TEXT WITHOUT ANY ADDITIONAL TEXT OR MARKUP.
                    """,
                },
            ])
        # Return the content of the response
        if not response.choices or not response.choices[0].message:
            logger.error("No message returned in the first choice.")
            return "llm_error"
        return str(response.choices[0].message.content).strip()
    except Exception as e:
        logger.error("Error during translation:")
        logger.error(e)
        # Raise the exception to be caught in the calling function
        raise e

@app.route('/')
def index():
    """
    Home route to check if the server is running.
    """
    return send_file('index.html')

@app.route('/api/webhook/transcript', methods=['POST'])
def transcript_webhook():
    """
    Handle webhook events from Recall AI for transcript data.
    """
    logger.info(f"Received webhook transcription request")
    try:
        logger.info("request.json",request.json)
        words_array = request.json['data']['data']['words']
        bot_id = request.json['data']['bot']['id']

        if not words_array or not bot_id:
            logger.error("No words or bot_id found in the request")
            return Response("No words or bot_id found", status=400)

        for word_obj in words_array:
            text = word_obj['text']
            try:
                # Translate the text to Spanish
                translated_text = translate_text(text)
                if translated_text == "llm_error":
                    logger.error("Error translating text:", text)
                    continue
                text = translated_text
            except Exception as e:
                logger.error(f"Error translating text '{text}':", e)
                continue
            response = requests.post(f'{WEBHOOK_BASE_URL}/api/bot/{bot_id}/message', json={
                'message': text
            })
            if response.status_code != 200:
                logger.error(f"Failed to send message to bot {bot_id}: {response.json()}")

        logger.info("All words processed successfully")

    except Exception as e:
        logger.error("Error parsing JSON:", e)
        return Response("Invalid JSON", status=400)


    return Response("Webhook received", status=200)

# @app.route('/api/webhook/recall', methods=['POST'])
# def recall_webhook():
#     """
#     Handle webhook events from Recall AI.
#     """
#     logger.info("Received webhook request")
#     headers = request.headers
#     payload = request.data

#     try:
#         wh = Webhook(RECALL_WEBHOOK_SIGNING_SECRET)
#         msg = wh.verify(payload, headers)
#         if msg['event'] in ['transcript.partial_data', 'transcript.done', 'transcript.processing']:
#             logger.info("Received transcript successfully:", msg)
#         return jsonify({"status": "success", "message": "Webhook received"}), 200
#     except WebhookVerificationError as e:
#         return jsonify({"error": e}), 400

@app.route('/join', methods=['POST'])
def create_bot_for_meeting():
    """
    Create a bot for the given meeting URL.
    """
    meeting_url = request.json['meeting_url']
    if not meeting_url:
        return jsonify({"error": "meeting_url is required"}), 400

    url = RECALL_BASE_URL
    headers = {
        "Authorization": RECALL_API_TOKEN,
        "accept": "application/json",
        "content-type": "application/json"
    }
    body = {
        "meeting_url": meeting_url,
        "recording_config": {
            "transcript": {
                "provider": {
                    "meeting_captions": {},
                }
            },
            "realtime_endpoints": [
                {
                    "type": "webhook",
                    "url": f"{WEBHOOK_BASE_URL}/api/webhook/transcript",
                    "events": ["transcript.data", "transcript.partial_data"]
                }
            ]
        }
    }
    response = requests.post(url, headers=headers, json=body)
    if response.status_code != 200:
        return jsonify({"error": "Failed to create bot", "details": response.json()}), response.status_code

    # Response will have bot ID and data download URL
    response_json = response.json()
    bot_id = response_json['id']
    logger.info(f"Bot {bot_id} created successfully:", response.json())

    return jsonify({
        "message": f"Bot created for {meeting_url}"
    }), 200

@app.route('/api/bot/<bot_id>/message', methods=['POST'])
def send_message(bot_id):
    """
    Send a message to the Recall AI bot to send to the meeting chat.
    https://docs.recall.ai/reference/bot_send_chat_message_create
    """
    url = f"{RECALL_BASE_URL}/{bot_id}/send_chat_message/"
    headers = {
        "Authorization": RECALL_API_TOKEN,
        "accept": "application/json",
        "content-type": "application/json"
    }
    message = request.json.get('message')
    if not message:
        message = "Hello from Recall AI bot! This is a default message."
    body = {
        # TODO add transcribed messages....
        "message": message
    }
    response = requests.post(url, headers=headers, json=body)
    if response.status_code != 200:
        return jsonify({"error": "Failed to send message", "details": response.json()}), response.status_code
    logger.info("Message sent successfully:", response.json())
    return jsonify({
        "message": f"Message sent to bot {bot_id}"
    }, 200)

@app.route('/api/bot/<bot_id>/transcript', methods=['GET'])
def get_transcript_for_bot(bot_id):
    """
    Get the transcript for the given bot ID.
    """
    logger.info("Retrieving transcript for bot ID:", bot_id)

    url = f"{RECALL_BASE_URL}/{bot_id}"
    headers = {
        "Authorization": RECALL_API_TOKEN,
        "accept": "application/json",
    }

    bot_response = requests.get(url, headers=headers)
    if bot_response.status_code != 200:
        return jsonify({"error": "Failed to get bot data", "details": bot_response.json()}), bot_response.status_code
    try:
        bot_data = bot_response.json()
        transcript_url = bot_data['recordings'][0]['media_shortcuts']['transcript']['data']['download_url']
        logger.info("Transcript url retrieved successfully:", transcript_url)
    except Exception as e:
        return jsonify({"error": "Failed to parse bot data", "details": str(e)}), 500

    # Download the transcript
    if not transcript_url:
        return jsonify({"error": "Transcript URL not found in bot data"}), 404

    transcript_response = requests.get(transcript_url)
    if transcript_response.status_code != 200:
        return jsonify({"error": "Failed to download transcript", "details": transcript_response.json()}), transcript_response.status_code
    logger.info("Transcript downloaded successfully")
    return Response(transcript_response.content, mimetype='application/json')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
