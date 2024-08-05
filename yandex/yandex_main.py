import logging
import os
import shutil
import requests
import socket
from urllib.parse import urlparse, urlunparse
from collections import OrderedDict
from pprint import pprint

logging.basicConfig(level=logging.INFO)

# TODO: Добавить обработку события, в случае неверного токена или окончания его срока работы
def get_yandex_user_id(user_id, yandex_user_token):
    # https://yandex.ru/dev/webmaster/doc/dg/reference/user.html
    response = requests.get("https://api.webmaster.yandex.net/v4/user", headers = {"Authorization": f'OAuth {yandex_user_token}'})
    responseJSON = response.json()
    logging.info(f"[{user_id}] Получен уникальный идентификатор пользователя Яндекс (yandexUserID = {str(responseJSON['user_id'])})")
    return str(responseJSON['user_id'])

def get_webmaster_site_list(user_id, yandex_user_token, yandex_user_id):
    # https://yandex.ru/dev/webmaster/doc/dg/reference/hosts.html
    response = requests.get("https://api.webmaster.yandex.net/v4/user/" + yandex_user_id + "/hosts", headers = {"Authorization": f'OAuth {yandex_user_token}'})
    # logging.info(f"[{user_id}] Получен список сайтов для {yandex_user_id}: {response.json()}")
    logging.info(f"[{user_id}] Получен список сайтов для {yandex_user_id}")
    return response.json()

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
        return None

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
                # TODO: Добавить диалоговое окно о продолжении или прекращении работы
                break
    else:
        logging.error(f"[{user_id}] Сайт не добавлен в Яндекс.Вебмастер или возникла внутреняя ошибка.")
        # TODO: Добавить диалоговое окно о продолжении или прекращении работы

def getYandexRecrawlQuota():
    # https://yandex.ru/dev/webmaster/doc/dg/reference/host-recrawl-quota-get.html
    # TODO: Разработать функцию
    return

def getYandexNotIndexedPage():
    # https://www.marronnier.ru/blog/13-avtomatizatsiya/57-indeksirovanie-sajtov-s-pomoshchyu-yandeks-vebmaster-api-na-python
    # TODO: Разработать функцию
    return