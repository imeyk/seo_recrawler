import logging
import os
import httplib2
import json
from oauth2client.service_account import ServiceAccountCredentials

# TODO: Добавить обработчики ошибок
def google_publish(user_id, indexing_api_key='', url=''):
    print(f"indexing_api_key = {indexing_api_key}")
    print(f"URL to Google Indexing API = {url}")

    SCOPES = ["https://www.googleapis.com/auth/indexing"]
    
    # Загрузка ключа JSON и удаление нежелательных ключей
    service_account_info = json.loads(indexing_api_key)
    # Удалите ключ universe_domain, если он присутствует
    service_account_info.pop('universe_domain', None)
    
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scopes=SCOPES)
    http = credentials.authorize(httplib2.Http())

    ENDPOINT = "https://indexing.googleapis.com/v3/urlNotifications:publish"
    
    # TODO: Добавить валидацию URL, не работает без http... (при отправке только домена)
    content = {
        'url': url.strip(),
        'type': "URL_UPDATED"
    }
    json_ctn = json.dumps(content)
        
    response, content = http.request(ENDPOINT, method="POST", body=json_ctn)
    result = json.loads(content.decode())

    if "error" in result:
        logging.error(f"[{user_id}] Google Indexing API: {result['error']['code']} - {result['error']['status']}): {result['error']['message']}")
        return(f"\n🔴 Google Indexing API: Ошибка отправки: {result['error']['code']} - {result['error']['status']}): {result['error']['message']}")
    else:
        logging.info(f"[{user_id}] Google Indexing API: {result['urlNotificationMetadata']['latestUpdate']['type']} {result['urlNotificationMetadata']['url']} {result['urlNotificationMetadata']['latestUpdate']['notifyTime']}")
        return("\n🟢 Google Indexing API: Отправлено на переобход")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s / %(levelname)s / %(message)s', datefmt='%d.%m.%y %H:%M:%S')
    google_publish("Test", os.getenv("test_indexing_api_key"), os.getenv("test_indexing_api_url"))