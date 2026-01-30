import requests
import os
import json
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# ========== CONFIG ==========
XBYTE_API_URL = "https://quickcommerce-india-api.xbyteapi.com/quickcommerce_india"
XBYTE_API_KEY = "9noci65oeogu990eag2zlrzu1"
KEYWORD = "maggi masala"
PINCODE = "560001"
PLATFORM = "instamart"

# The data to be sent, as a Python dictionary
payload = {
    "api_key": XBYTE_API_KEY,
    "endpoint": "result",
    "keyword": KEYWORD,
    "zipcode": PINCODE,
    "platform": PLATFORM
}

# Send the POST request with the 'json' parameter
response = requests.post(XBYTE_API_URL, json=payload)

# Check the response status code
if response.status_code == 200:
    print('Request successful!')
    # Print the JSON response from the server
    print(response.json())
else:
    print(f'An error occurred: {response.status_code}')
