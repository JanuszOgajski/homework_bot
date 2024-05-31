from http import HTTPStatus
import logging
import os
import requests
import time

from dotenv import load_dotenv
from telebot import TeleBot

from exceptions import (
    APIError
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

logging.basicConfig(
    format='%(asctime)s, %(levelname)s, %(message)s',
    level=logging.DEBUG,
)


def check_tokens():
    """Проверяет доступность переменных окружения."""
    tokens = (
        PRACTICUM_TOKEN,
        TELEGRAM_TOKEN,
        TELEGRAM_CHAT_ID,
    )
    logging.debug('Проверяем токены')
    for token in tokens:
        if token is None:
            logging.critical('a required environment variable is None')
            raise SystemExit


def send_message(bot, message):
    """Отправляет сообщение в Telegram-чат."""
    delivered = True
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.debug('отправлено')
    except Exception as error:
        delivered = False
        message = f'Сбой в работе программы: {error}'
        logging.error(message)
    finally:
        return delivered


def get_api_answer(timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    payload = {'from_date': timestamp}
    result = {}
    try:
        statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=payload
        )
    except requests.RequestException as error:
        logging.error(f'api {error}')
    if statuses.status_code != HTTPStatus.OK:
        raise APIError('ty choto zabyl v api')
    result = statuses.json()
    logging.debug(f'api {result}')
    return result


def check_response(response):
    """Проверяет ответ API на соответствие документации из урока."""
    if type(response) is not dict:
        raise TypeError('response не тот тип')
    elif 'homeworks' not in response.keys():
        raise KeyError('key error in response')
    elif type(response['homeworks']) is not list:
        raise TypeError('response не тот тип2')
    response = response['homeworks']
    logging.debug(f'response {response}')
    return response


def parse_status(homework):
    """Извлекает статус о конкретной домашней работе."""
    try:
        homework_name = homework['homework_name']
        if homework_name is None:
            raise KeyError('нет домашки')
    except KeyError:
        pass
    if homework['status'] in HOMEWORK_VERDICTS.keys():
        verdict = HOMEWORK_VERDICTS[homework['status']]
    logging.debug(f'parse status {homework_name} {verdict}')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    logging.debug(f'Установлен таймстемп {timestamp}')
    previous_status = ''

    while True:
        try:
            response = get_api_answer(timestamp)
            if response is not []:
                homework = check_response(response)[0]
                updated_status = parse_status(homework)
                if updated_status != previous_status:
                    if send_message(bot, updated_status):
                        previous_status = updated_status
                        timestamp = int(time.time())
                        logging.debug(f'Установлен таймстемп {timestamp}')
        except IndexError:
            logging.warning('no homeworks in response')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            failure_message = message
            logging.error(message)

            if message == failure_message:
                if send_message(bot, message):
                    failure_message = message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
