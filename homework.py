import logging
import os
import time
from http import HTTPStatus

import requests
from dotenv import load_dotenv
from telebot import TeleBot, apihelper

from exceptions import (
    APIError,
    APIRequestError,
    EmptyResponseAPIError,
    MissingVariableError,
)

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяет доступность переменных окружения."""
    tokens = (
        PRACTICUM_TOKEN,
        TELEGRAM_TOKEN,
        TELEGRAM_CHAT_ID,
    )
    logging.debug('Проверяем токены')
    if not all(tokens):
        logging.critical('a required environment variable is None')
        raise MissingVariableError('Нет переменной(-ых) окружения')


def send_message(bot, message):
    """Отправляет сообщение в Telegram-чат."""
    delivered = True
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.debug('отправлено')
    except apihelper.ApiException as error:
        delivered = False
        message = f'Сбой в работе программы: {error}'
        logging.error(message)
    finally:
        return delivered


def get_api_answer(timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    api_dict = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': timestamp}
    }
    try:
        logging.debug(
            'запрос с параметрами: {url} {headers} {params}'.format(**api_dict)
        )
        statuses = requests.get(**api_dict)
    except requests.RequestException as error:
        raise APIRequestError(f'Получена ошибка {error}')
    if statuses.status_code != HTTPStatus.OK:
        raise APIError('Не получен статус ответа 200')
    result = statuses.json()
    logging.debug(f'api {result}')
    return result


def check_response(response):
    """Проверяет ответ API на соответствие документации из урока."""
    if not isinstance(response, dict):
        raise TypeError('в response не передан словарь')
    if 'homeworks' not in response.keys():
        raise EmptyResponseAPIError('в ответе API нет "homeworks"')
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise TypeError('под ключом homeworks не было списка')
    logging.debug(f'response {homeworks}')
    return homeworks


def parse_status(homework):
    """Извлекает статус о конкретной домашней работе."""
    if 'homework_name' in homework.keys():
        homework_name = homework['homework_name']
    else:
        raise KeyError('Нет ключа в parse_status')
    if not homework['status']:
        raise KeyError('Нет ключа в parse_status')
    if homework['status'] in HOMEWORK_VERDICTS.keys():
        verdict = HOMEWORK_VERDICTS[homework['status']]
    else:
        raise KeyError('Нет ключа в parse_status')
    logging.debug(f'parse status {homework_name} {verdict}')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = 0
    logging.debug(f'Установлен таймстемп {timestamp}')
    previous_status = ''

    while True:
        try:
            response = get_api_answer(timestamp)
            timestamp = response.get('current_date', timestamp)
            logging.debug(f'Установлен таймстемп {timestamp}')
            homework = check_response(response)
            updated_status = ''
            if homework:
                updated_status = parse_status(homework[0])
            else:
                logging.debug('нет новых статусов')
                previous_status = ''
            if updated_status != previous_status:
                if send_message(bot, updated_status):
                    previous_status = updated_status
        except EmptyResponseAPIError as error:
            logging.error(f'нет домашек в ответе: {error}')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            if previous_status != message:
                send_message(bot, message)
                previous_status = ''
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s, %(levelname)s, %(message)s',
        level=logging.DEBUG,
    )
    main()
