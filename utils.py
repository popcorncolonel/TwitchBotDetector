import requests 
from get_passwords import CLIENT_ID

def get_json_response(url):
    try:
        req = requests.get(url, headers={"Client-ID": CLIENT_ID})
        data = req.json()
        return data
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception as e:
        print("Error getting " + url + ":", e)
        return []

