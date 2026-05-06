import os
from dotenv import load_dotenv

load_dotenv("/Users/grubby/Library/Mobile Documents/com~apple~CloudDocs/PycharmProjects/langgrap/evn")
api_key = os.getenv("SILICON_FLOW")
base_url = os.getenv("SILICON_URL")
api_tavily = os.getenv("api_tavily")

