import logging
import requests

# Настройка логирования
logging.basicConfig(level=logging.INFO)

def check_valid_url(user_id, url, check_domain=True):
    prefixes = ['https://', 'http://', 'http://www.', 'https://www.']
    tried_urls = set()

    if check_domain:
        # Если проверяем домен, добавляем префиксы
        if url.startswith('http://') or url.startswith('https://'):
            urls_to_try = [url]
        else:
            urls_to_try = [prefix + url for prefix in prefixes]
    else:
        # Если не проверяем домен, используем URL как есть
        urls_to_try = [url]

    for url_to_check in urls_to_try:
        # Избегаем повторных проверок одного и того же URL
        if url_to_check in tried_urls:
            continue
        tried_urls.add(url_to_check)
        try:
            response = requests.get(url_to_check, timeout=10)
            status_code = response.status_code
            logging.info(f'{user_id} URL: {url_to_check}, Код статуса: {status_code}')
            # Если произошел редирект
            if response.history:
                final_url = response.url
                logging.info(f'{user_id} Перенаправлено на: {final_url}')
                # Выходим из цикла после первого редиректа
                return final_url
            else:
                # Если нет редиректов, выходим из цикла
                return url_to_check
        except requests.exceptions.RequestException as e:
            logging.error(f'{user_id} Ошибка при доступе к {url_to_check}: {e}')
            # Переходим к следующему префиксу, если есть ошибка
            continue

if __name__ == '__main__':
    # url = input('Введите домен или URL: ')
    # check_domain_input = input('Проверять как домен? (True/False): ')
    # check_domain = check_domain_input.strip().lower() == 'true'
    # check_status_code(url, check_domain=True)

    print (check_valid_url(user_id='test', url='x-profil.ru', check_domain=True))
    '''
    check_status_code('www.x-profil.ru')
    check_status_code('x-profil.ru')
    check_status_code('www.x-profil.ru')
    check_status_code('x-profil.by')
    check_status_code('asasasdsadsad')
    check_status_code('asasasdsadsad.com')
    '''