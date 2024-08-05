import logging
import requests
import json
import re

# TODO: Переписать на отправку пачки запросов а не по одному
def indexnow_publish(user_id, project_url=None, indexnow=False, indexnow_key=None, indexnow_key_path=None, indexnow_service=["yandex", "bing"], line=None):
    headers = {
        "Content-Type": "application/json"
    }
    
    payload = {
        "host": re.sub(r'^(https?://)?(www\.)?', '', project_url).rstrip('/'),  # Замените на ваш домен
        "key": indexnow_key,
        "keyLocation": indexnow_key_path,
        "urlList": line
    }

    print(f"Indexnow_service == {indexnow_service}")
    print(f"Line == {line}")
    if 'bing' in indexnow_service:
        bing_response = requests.post('https://www.bing.com/indexnow', headers=headers, data=json.dumps(payload))
        print(f"Bing response: {bing_response.status_code}, {bing_response.text}")
        
    if 'yandex' in indexnow_service:
        yandex_response = requests.post('https://yandex.com/indexnow', headers=headers, data=json.dumps(payload))
        print(f"Yandex response: {yandex_response.status_code}, {yandex_response.text}")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s', datefmt='%H:%M:%S %d.%m.%y')
    
    indexnow_publish(user_id, project_url, indexnow, key, key_location, indexnow_service=engines, line=urls)

