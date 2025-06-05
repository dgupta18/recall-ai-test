import os
import requests
from dotenv import load_dotenv
from flask import Flask, request, jsonify, send_file, Response

load_dotenv()
RECALL_API_TOKEN = os.getenv('RECALL_API_TOKEN')

# https://docs.recall.ai/docs/meeting-caption-transcription
app = Flask(__name__)

@app.route('/')
def index():
    """
    Home route to check if the server is running.
    """
    return Response("Recall AI Bot Server is running", status=200)

@app.route('/api/bot/<meeting_url>', methods=['POST'])
def create_bot_for_meeting(meeting_url):
    """
    Create a bot for the given meeting URL.
    """

    # url = "https://us-west-2.recall.ai/api/v1/bot/"
    # headers = {
    #     "Authorization": RECALL_API_TOKEN,
    #     "accept": "application/json",
    #     "content-type": "application/json"
    # }
    # body = {
    #     "meeting_url": meeting_url,
    #     "recording_config

    pass