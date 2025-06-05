import os
import requests
from dotenv import load_dotenv
from flask import Flask, request, jsonify, Request, Response, send_file
from svix.webhooks import Webhook, WebhookVerificationError

app = Flask(__name__)
load_dotenv()
RECALL_API_TOKEN = os.getenv('RECALL_API_TOKEN')
RECALL_WEBHOOK_SIGNING_SECRET = os.getenv('RECALL_WEBHOOK_SIGNING_SECRET')
WEBHOOK_BASE_URL = os.getenv('WEBHOOK_BASE_URL', 'http://localhost:8080')
USING_PROVIDER = False

@app.route('/')
def index():
    """
    Home route to check if the server is running.
    """
    return send_file('index.html')

@app.route('/api/webhook/recall', methods=['POST'])
def recall_webhook():
    """
    Handle webhook events from Recall AI.
    """
    print("Received webhook request")
    headers = request.headers
    payload = request.data
    
    try:
        wh = Webhook(RECALL_WEBHOOK_SIGNING_SECRET)
        msg = wh.verify(payload, headers)
        print('Webhook event-' + msg['event'])
        if msg['event'] in ['transcript.partial_data', 'transcript.done', 'transcript.processing']:
            print("Received transcript successfully:", msg)
        return jsonify({"status": "success", "message": "Webhook received"}), 200
    except WebhookVerificationError as e:
        return jsonify({"error": e}), 400

@app.route('/join', methods=['POST'])
def create_bot_for_meeting():
    """
    Create a bot for the given meeting URL.
    To try this endpoint with curl:
    curl -X POST http://localhost:8080/join \
    -H "Content-Type: application/json" \
    --data '{"meeting_url": "<meeting_url>"}'
    where <meeting_url> is the URL of the meeting you want to join.
    """
    meeting_url = request.json['meeting_url']
    if not meeting_url:
        return jsonify({"error": "meeting_url is required"}), 400

    url = "https://us-west-2.recall.ai/api/v1/bot/"
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
            "recording_config": {
                "realtime_endpoints": [
                    {
                        "type": "webhook",
                        "url": f"{WEBHOOK_BASE_URL}/api/webhook/recall",
                        "events": ["transcript.data", "transcript.partial_data"]
                    }
                ]
            }
        }
    }
    # if USING_PROVIDER:
    #     data = {
    #         "meeting_url": meeting_url,
    #         "recording_config": {
    #             "transcript": {
    #                 "provider": {
    #                     "assembly_ai_streaming": {}
    #                 }
    #             },
    #             "realtime_endpoints": [
    #                 {
    #                     "type": "webhook",
    #                     "url": f"{BASE_URL}/api/webhook/recall/transcript",
    #                     "events": ["transcript.data", "transcript.partial_data"]
    #                 }
    #             ]
    #         }
    #     }
    
    response = requests.post(url, headers=headers, json=body)
    if response.status_code != 200:
        return jsonify({"error": "Failed to create bot", "details": response.json()}), response.status_code

    # Response will have bot ID and data download URL
    response_json = response.json()
    bot_id = response_json['id']
    print(f"Bot {bot_id} created successfully:", response.json())

    # download_url = response_json['recordings'][0]['media_shorcuts']['transcript']['data']['download_url']

    # # Get transcript
    # transcript_response = requests.get(download_url)
    # if transcript_response.status_code != 200:
    #     return jsonify({"error": "Failed to download transcript", "details": transcript_response.json()}), transcript_response.status_code 
    
    # print("Transcript downloaded successfully")
    # print(transcript_response.json())

    return jsonify({
        "message": f"Bot created for {meeting_url}"
    }), 200

@app.route('/api/bot/<bot_id>/message', methods=['POST'])
def send_message(bot_id):
    """
    Send a message to the Recall AI bot to send to the meeting chat.
    https://docs.recall.ai/reference/bot_send_chat_message_create
    """
    url = f"https://us-west-2.recall.ai/api/v1/bot/{bot_id}/send_chat_message/"
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
    print("Message sent successfully:", response.json())
    return jsonify({
        "message": f"Message sent to bot {bot_id}"
    }), 200

@app.route('/api/bot/<bot_id>/transcript', methods=['GET'])
def get_transcript_for_bot(bot_id):
    """
    Get the transcript for the given bot ID.
    """
    print("IN get_transcript_for_bot")
    url = f"https://us-west-2.recall.ai/api/v1/bot/{bot_id}"
    headers = {
        "Authorization": RECALL_API_TOKEN,
        "accept": "application/json",
    }
    
    print("ID::::",bot_id)
    bot_response = requests.get(url, headers=headers)
    print("Bot response:", bot_response.json())
    print("Bot response status code:", bot_response.status_code)
    if bot_response.status_code != 200:
        return jsonify({"error": "Failed to get bot data", "details": bot_response.json()}), bot_response.status_code
    try:
        bot_data = bot_response.json()
        transcript_url = bot_data['recordings'][0]['media_shortcuts']['transcript']['data']['download_url']
        print("Transcript url retrieved successfully:", transcript_url)
    except Exception as e:
        return jsonify({"error": "Failed to parse bot data", "details": str(e)}), 500
    
    # Download the transcript
    if not transcript_url:
        return jsonify({"error": "Transcript URL not found in bot data"}), 404
    
    transcript_response = requests.get(transcript_url)
    if transcript_response.status_code != 200:
        return jsonify({"error": "Failed to download transcript", "details": transcript_response.json()}), transcript_response.status_code
    print("Transcript downloaded successfully")
    return Response(transcript_response.content, mimetype='application/json')

@app.route('/api/transcript/<download_url>', methods=['GET'])
def get_transcript_from_url(download_url):
    response = requests.get(download_url)
    if response.status_code != 200:
        return jsonify({"error": "Failed to download transcript", "details": response.json()}), response.status_code
    print("Transcript downloaded successfully")
    return Response(response.content, mimetype='application/json')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
