import logging
import requests
from urllib.parse import urlparse

# TODO: Добавить определение http://, https://, http://www., https://www.
# TODO: При проверке статус-кода сайта, проблема с редиректами на сайтах (пример x-profil.ru)
# Функция проверки валидности URL и отключения редиректов
def check_valid_url(user_id, url, check_domain=False):
    logging.info(f"[{user_id}] Начат процесс проверки URL {url} на валидность без редиректов")

    # Добавление схемы, если она отсутствует
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url

    try:
        # Отправляем запрос без редиректов
        response = requests.get(url, timeout=5, allow_redirects=False)
    except requests.exceptions.RequestException as e:
        logging.error(f"[{user_id}] Ошибка при подключении к {url}: {e}")
        return None

    # Проверка статуса ответа
    if response.status_code == 200:
        logging.info(f"[{user_id}] Получен успешный ответ (200) от {url}")
    elif 300 <= response.status_code < 400:
        # Если мы получили редирект, логируем местоположение редиректа
        redirect_url = response.headers.get('Location')
        logging.warning(f"[{user_id}] Редирект на {redirect_url}")
        return redirect_url
    else:
        logging.error(f"[{user_id}] Неверный статус код {response.status_code} при попытке доступа к {url}")
        return None

    # Получаем конечный URL без редиректа
    final_url = response.url
    parsed_final_url = urlparse(final_url)
    hostname = parsed_final_url.netloc
    scheme = parsed_final_url.scheme

    # Проверка схемы протокола (поддерживаются http://, https://)
    if not (scheme in ['http', 'https'] and hostname.startswith(('www.', ''))):
        logging.error(f"[{user_id}] Неподдерживаемый URL {final_url}")
        return None

    logging.info(f"[{user_id}] Конечный URL после проверки: {final_url}")

    if check_domain:
        # Возвращаем только домен с протоколом
        domain_url = f"{scheme}://{hostname}/"
        logging.info(f"[{user_id}] Возвращаем домен: {domain_url}")
        return domain_url
    else:
        # Возвращаем полный URL
        return final_url

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s', datefmt='%H:%M:%S %d.%m.%Y')

    user_id = 666666
    # url = "imeyk.ru"  # Вводим URL
    # check_domain = False  # Установите True, чтобы возвращать только домен
    url = "https://www.x-profil.by"
    check_domain = True

    result = check_valid_url(user_id, url, check_domain)
    if result:
        print(f"Финальный URL: {result}")
    else:
        print("Ошибка при проверке URL")