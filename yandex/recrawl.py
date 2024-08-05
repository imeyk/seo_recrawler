import logging
import os
import requests
from pprint import pprint
import socket
from urllib.parse import urlparse, urlunparse

# TODO: Добавить обработку события, в случае неверного токена или окончания его срока работы
def get_yandex_user_id(user_id, yandex_user_token):
    # https://yandex.ru/dev/webmaster/doc/dg/reference/user.html
    response = requests.get("https://api.webmaster.yandex.net/v4/user", headers = {"Authorization": f'OAuth {yandex_user_token}'})
    responseJSON = response.json()
    logging.info(f"responseJSON = {responseJSON}")
    if "error_code" in responseJSON:
        logging.error("Ошибка!")
        return False
    elif "user_id" in responseJSON:
        logging.info(f"[{user_id}] Получен уникальный идентификатор пользователя Яндекс (yandexUserID = {str(responseJSON['user_id'])})")
        return str(responseJSON['user_id'])
    else:
        logging.critical("Неизвестная ошибка!")
        return False

def get_webmaster_site_list(user_id, yandex_user_token, yandex_user_id):
    # https://yandex.ru/dev/webmaster/doc/dg/reference/hosts.html
    response = requests.get("https://api.webmaster.yandex.net/v4/user/" + yandex_user_id + "/hosts", headers = {"Authorization": f'OAuth {yandex_user_token}'})
    # logging.info(f"[{user_id}] Получен список сайтов для {yandex_user_id}: {response.json()}")
    logging.info(f"[{user_id}] Получен список сайтов для {yandex_user_id}")
    return response.json()

def get_webmaster_host_id(user_id, domain, webmaster_site_list):
    # TODO: Нужна ли проверка URL?
    for hostURL in webmaster_site_list['hosts']:
        if hostURL['ascii_host_url'] == domain:
            if hostURL['verified'] == True:
                logging.info(f"[{user_id}] Сайт {hostURL['ascii_host_url']} обнаружен и имеет верификацию в сервисе Яндекс.Вебмастер")
                return hostURL['host_id']
                break
            else:
                logging.error(f"[{user_id}] Сайт обнаружен, но не подтвержден в сервисе Яндекс.Вебмастер.")
                return("\n🔴 Яндекс.Вебмастер: Ошибка отправки. Не подтверждены права на сайт")
                # TODO: Добавить диалоговое окно о продолжении или прекращении работы
    else:
        logging.error(f"[{user_id}] Не подтверждены права на сайт в Яндекс.Вебмастер или возникла внутреняя ошибка")
        return("\n🔴 Яндекс.Вебмастер: Ошибка отправки. Не подтверждены права на сайт, или возникла внутреняя ошибка")
        # TODO: Добавить диалоговое окно о продолжении или прекращении работы

# TODO: Нужна ли проверка на правописания домена с WWWW или без
def check_valid_url(user_id, url, check_domain=False):
    logging.info(f"[{user_id}] Начат процесс проверки URL {url} на валидность")
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url

    parsed_url = urlparse(url)
    hostname = parsed_url.netloc or parsed_url.path

    # Проверяем доступность ресурса по HTTP
    try:
        with socket.create_connection((hostname, 80), timeout=5):
            # logging.info("Определено наличие http:// протокола")
            scheme = 'http'
    except Exception:
        scheme = None

    # Если ресурс доступен по HTTP, проверяем доступность по HTTPS
    if scheme:
        try:
            with socket.create_connection((hostname, 443), timeout=5):
                # logging.info("Определено наличие https:// протокола")
                scheme = 'https'
        except Exception:
            pass

    # Если ресурс недоступен и по HTTP, и по HTTPS, возвращаем ошибку
    if not scheme:
        logging.error(f"[{user_id}] Ресурс {scheme}://{hostname} недоступен")
        return(f"\n🔴 Яндекс.Вебмастер: Ошибка отправки. Ресурс {scheme}://{hostname} недоступен")
        
    logging.info(f"[{user_id}] Используем протокол {scheme} для проекта")

    if check_domain == True:
        # Формируем и возвращаем только домен сайта
        url = f"{scheme}://{hostname}/"
        logging.info(f"[{user_id}] Формируем и возвращаем URL домена: {url}")
        if not parsed_url.path or parsed_url.path == hostname:
            path = '/'
        else:
            path = parsed_url.path
        return url
    else:
        # Формируем и возвращаем введенный url
        url = urlunparse((scheme, hostname, parsed_url.path, '', '', ''))
        logging.info(f"[{user_id}] Формируем и возвращаем полный URL: {url}")
        return url

def yandex_recrawl(user_id, yandex_user_token='', line=''):
    yandex_user_id = get_yandex_user_id(user_id, yandex_user_token)
    if yandex_user_id != False:
        webmaster_site_list = get_webmaster_site_list(user_id, yandex_user_token, yandex_user_id)
        domain = check_valid_url(user_id, line, check_domain=True)
        webmaster_host_id = get_webmaster_host_id(user_id, domain, webmaster_site_list)
    else:
        return(f"\n🔴 Яндекс.Вебмастер: Невалидный токен")
    
    # https://yandex.ru/dev/webmaster/doc/dg/reference/host-recrawl-post.html
    data = {"url": f"{line}"}
    response = requests.post("https://api.webmaster.yandex.net/v4/user/" + yandex_user_id + "/hosts/" + webmaster_host_id + "/recrawl/queue", json = data, headers = {"Authorization": f'OAuth {yandex_user_token}'})
    pprint(response.json())
    # TODO: Добавить обработчики негативных событий
    return("\n🟢 Яндекс.Вебмастер: Отправлено на переобход") # response.json()
    
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s / %(levelname)s / %(message)s', datefmt='%d.%m.%y %H:%M:%S')
    yandex_recrawl("Test", os.getenv("test_webmaster_user_token"), os.getenv("test_webmaster_url"))