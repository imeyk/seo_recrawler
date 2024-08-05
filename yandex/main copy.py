import logging
import os
import shutil
import requests
from collections import OrderedDict
from pprint import pprint

logging.basicConfig(level=logging.INFO)
tokenYandex = "y0_AgAEA7qjXNyqAAtW1gAAAAD78bgpAAB9YLTM4F9A2KQroCwsrdQANDMufQ"

def getYandexUserID():
    # https://yandex.ru/dev/webmaster/doc/dg/reference/user.html
    response = requests.get("https://api.webmaster.yandex.net/v4/user", headers = {"Authorization": f'OAuth {tokenYandex}'})
    responseJSON = response.json()
    global yandexUserID
    yandexUserID = str(responseJSON['user_id'])
    logging.info(f"Получен уникальный идентификатор пользователя Яндекс (yandexUserID = {yandexUserID})")
    # TODO: Добавить обработку события, в случае неверного токена или окончания его срока работы

def getYandexSiteList():
    # https://yandex.ru/dev/webmaster/doc/dg/reference/hosts.html
    response = requests.get("https://api.webmaster.yandex.net/v4/user/" + yandexUserID + "/hosts", headers = headers)
    global yandexSiteList
    yandexSiteList = response.json()
    logging.info("Список сайтов добавленных в сервис Яндекс.Вебмастер – успешно получен.")

def getYandexHostID():
    # TODO: Добавить замену переменной url на сайт из первой строки txt файла или сообщения телеграмм
    url = "https://x-profil.ru/"
    for hostURL in yandexSiteList['hosts']:
        if hostURL['ascii_host_url'] == url:
            if hostURL['verified'] == True:
                global yandexHostID
                yandexHostID = hostURL['host_id']
                logging.info(f"Сайт {hostURL['ascii_host_url']} обнаружен и имеет верификацию в сервисе Яндекс.Вебмастер.")
                break
            else:
                logging.error("Сайт обнаружен, но не подтвержден в сервисе Яндекс.Вебмастер.")
                # TODO: Добавить диалоговое окно о продолжении или прекращении работы
                break
    else:
        logging.error("Сайт не добавлен в Яндекс.Вебмастер или возникла внутреняя ошибка.")
        # TODO: Добавить диалоговое окно о продолжении или прекращении работы

def postponeListRemoveDuplication():
    with open('postpone.txt', 'r') as file:
        lines = file.readlines()
        unique_lines = list(OrderedDict.fromkeys(line.strip() for line in lines if line.strip()))

    with open('postpone.txt', 'w') as file:
        for line in unique_lines:
            file.write(f"{line}\n")

    logging.info("Удаление дублей строк для файла списка URL отработавшими с ошибками – Завершена.")

def postYandexRecrawlEmptyStringCheck(line):
    # Пропуск пустой строки
    return len(line.strip()) > 0

def postYandexRecrawl():
    shutil.copy('urls.txt', 'urlsYandex.txt')
    with open('urlsYandex.txt', 'r') as file1, open('postpone.txt', 'a') as file2:
        for line in file1:
            try:
                if not postYandexRecrawlEmptyStringCheck(line):
                    # Если обработка не удалась, записываем строку в file2
                    file2.write(line)
                else:
                    # https://yandex.ru/dev/webmaster/doc/dg/reference/host-recrawl-post.html
                    data = {"url": f"{line}"}
                    response = requests.post("https://api.webmaster.yandex.net/v4/user/" + yandexUserID + "/hosts/" + yandexHostID + "/recrawl/queue", json = data, headers = headers)
                    pprint(response.json())
                    # TODO: Добавить обработчики негативных событий
            except Exception as e:
                # В случае любой ошибки также записываем строку в file2
                file2.write(line)

    os.remove('urlsYandex.txt')
    logging.info("Обработка строк файла urlsYandex.txt – Завершена.")
    
    postponeListRemoveDuplication()

def getYandexRecrawlQuota():
    # https://yandex.ru/dev/webmaster/doc/dg/reference/host-recrawl-quota-get.html
    # TODO: Разработать функцию
    return

def getYandexNotIndexedPage():
    # https://www.marronnier.ru/blog/13-avtomatizatsiya/57-indeksirovanie-sajtov-s-pomoshchyu-yandeks-vebmaster-api-na-python
    # TODO: Разработать функцию
    return

def main():
    global headers
    headers = {"Authorization": f'OAuth {tokenYandex}'}
    getYandexUserID()
    getYandexSiteList()
    getYandexHostID()
    postYandexRecrawl()
    # getYandexRecrawlQuota()
    # getYandexNotIndexedPage()

if __name__ == '__main__':
    main()