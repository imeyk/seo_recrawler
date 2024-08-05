"""
Файл отвечающий за отправку страниц на переобход при помощи технологии IndexNow

Args:
        user_id (str): ID пользователя
        project_url (str, optional): URL проекта
        indexnow (bool, optional): Флаг для включения IndexNow
        indexnow_key (str, optional): API ключ для IndexNow
        indexnow_key_path (str, optional): Путь к файлу с API ключом IndexNow
        indexnow_service (list, optional): Список поисковых систем для отправки (Yandex, Bing)
        line (str, optional): Строка для логирования
"""
import logging
import os
import requests

# Постраничная отправка в Яндекс
def indexnow_yandex_single(user_id, indexnow_key, indexnow_key_path, line):
    logging.info(f"{user_id} / IndexNow / Yandex / Инициализация постраничной отправки страниц")
    logging.info(f"{user_id} / IndexNow / Yandex / Обработка URL {line}")
    # TODO: Добавить keylocation https://yandex.ru/support/webmaster/indexnow/reference/get-url.html
    
    if indexnow_key_path:
        yandex_url = f"https://yandex.com/indexnow?url={line}&key={indexnow_key}&keyLocation={indexnow_key_path}"
    else:
        yandex_url = f"https://yandex.com/indexnow?url={line}&key={indexnow_key}"
    
    # Отправка на переобход
    # Справка по статус коду и описание ошибки https://yandex.ru/support/webmaster/indexnow/reference/get-url.html 
    response = requests.get(yandex_url)
    logging.info(f"{user_id} / IndexNow / Yandex / Статус код / {response.status_code}")
    logging.info(f"{user_id} / IndexNow / Yandex / Тело ответа / {response.text}")

    if response.status_code == 200:
        return(f"🟢 IndexNow (Yandex): Отправлено на переобход")
    elif response.status_code == 202:
        return(f"🟡 IndexNow (Yandex) {response.status_code}: Ожидается проверка ключа IndexNow")
    elif response == 403:
        return(f"🔴 IndexNow (Yandex) {response.status_code}: Ошибка. Ключ не удалось загрузить или он не подходит к указанным в запросе адресам")
    elif response == 405:
        return(f"🔴 IndexNow (Yandex) {response.status_code}: Ошибка. Поддерживаются методы GET и POST")
    elif response == 422:
        # TODO: Настроить вывод в зависимости от ошибки
        return(f"🔴 IndexNow (Yandex) {response.status_code}: Ошибка. {response.text}")
    elif response == 429:
        return(f"🔴 IndexNow (Yandex) {response.status_code}: Ошибка. Превышено количество запросов для одного IP-адреса")
    else:
        return(f"🔴 IndexNow (Yandex) {response.status_code}: Неизвестная ошибка. {response.text}")

def indexnow_bing_single(user_id, indexnow_key, indexnow_key_path, line):
    logging.info(f"{user_id} / IndexNow / Bing / Инициализация постраничной отправки страниц")
    logging.info(f"{user_id} / IndexNow / Bing / Обработка URL {line}")
    if indexnow_key_path:
        bing_url = f"https://www.bing.com/indexnow?url={line}&key={indexnow_key}&keyLocation={indexnow_key_path}"
    else:
        bing_url = f"https://www.bing.com/indexnow?url={line}&key={indexnow_key}"
    
    response = requests.post(bing_url)
    logging.info(f"{user_id} / IndexNow / Bing / Статус код / {response.status_code}")
    logging.info(f"{user_id} / IndexNow / Bing / Тело ответа / {response.text('message')}")

    if response.status_code == 200:
        return(f"🟢 IndexNow (Bing): Отправлено на переобход")
    elif response.status_code == 202:
        return(f"🟡 IndexNow (Bing) {response.status_code}: Ожидается проверка ключа IndexNow")
    elif response.status_code == 400:
        return(f"🔴 IndexNow (Bing) {response.status_code}: Ошибка. Неверный формат")
    elif response.status_code == 403:
        return(f"🔴 IndexNow (Bing) {response.status_code}: Ошибка. Ключ недействителен (например, ключ не найден, файл найден, но ключа нет в файле)")
    elif response.status_code == 422:
        return(f"🔴 IndexNow (Bing) {response.status_code}: Ошибка. Отправленные адреса не принадлежат хосту или ключ не соответствует схеме протоколу")
    elif response.status_code == 429:
        return(f"🔴 IndexNow (Bing) {response.status_code}: Ошибка. Слишком много запросов (потенциальный спам)")
    else:
        return(f"🔴 IndexNow (Bing) {response.status_code}: Неизвестная ошибка. {response.text}")

def indexnow_publish(user_id, project_url, indexnow_key=None, indexnow_key_path=None, indexnow_service=["yandex", "bing"], line=None):
    # TODO: Добавить инциализацию на отправку списка страниц, сейчас только отправка постранично https://yandex.ru/support/webmaster/indexnow/reference/post-url.html
    # TODO: Как вариант определять используется ли список адресов или str и в зависимости от этого действовать
    indexnow_service_yandex, indexnow_service_bing = None, None

    logging.info(indexnow_service)

    if "yandex" in indexnow_service:
        indexnow_service_yandex = "\n" + indexnow_yandex_single(user_id, indexnow_key, indexnow_key_path, line)
    else:
        logging.info(f"{user_id} / IndexNow / Yandex / Пропуск отправки на переобход")

    if "bing" in indexnow_service:
        indexnow_service_bing = "\n" + indexnow_bing_single(user_id, indexnow_key, indexnow_key_path, line)
    else:
        logging.info(f"{user_id} / IndexNow / Bing / Пропуск отправки на переобход")

    logging.info(f"{user_id} / IndexNow / Возвращаем ответ пользователю")
    return(f"{indexnow_service_yandex if indexnow_service_yandex else ''}\n{indexnow_service_bing if indexnow_service_bing else ''}")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s / %(levelname)s / %(message)s', datefmt='%d.%m.%y %H:%M:%S')
    print(indexnow_publish("Test", os.getenv("test_indexnow_project_url"), os.getenv("test_indexnow_key"), os.getenv("test_indexnow_key_path"), ["yandex", "bing"], os.getenv("test_indexnow_line")))