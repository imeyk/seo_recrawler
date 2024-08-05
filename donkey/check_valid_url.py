import logging
import socket
from urllib.parse import urlparse, urlunparse

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


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s', datefmt='%H:%M:%S %d.%m.%Y')
    
    user_id = 666666
    url = "imeyk.ru"
    # check_domain = False
    
    check_valid_url(user_id, url)