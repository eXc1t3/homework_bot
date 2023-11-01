import os
import time
import logging
from datetime import date
from xmlrpc.client import ResponseError

import requests
import telegram
from http import HTTPStatus

from dotenv import load_dotenv

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
    """Проверка наличия переменных среды."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot, message):
    """Отправка сообщения в Telegram."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug('Сообщение успешно отправлено.')
    except Exception as error:
        logging.error(
            f'Ошибка при отправке сообщения: {error}'
        )


class CustomAPIError(Exception):
    """Исключение, возникающее при ошибке запроса к API."""

    def __init__(self, message, endpoint=None, headers=None, params=None):
        self.message = message
        self.endpoint = endpoint
        self.headers = headers
        self.params = params

    def __str__(self):
        params_str = f'С параметрами: ' \
                     f'{self.endpoint}, {self.headers}, {self.params}' \
            if self.endpoint and self.headers and self.params else ''
        return f'Ошибка при запросе к API: {self.message}\n{params_str}'


def get_api_answer(timestamp):
    """Запрос к API Практикума."""
    params = {'from_data': timestamp}
    main_params = dict(url=ENDPOINT, headers=HEADERS, params=params)
    try:
        response = requests.get(**main_params)
    except Exception as error:
        raise CustomAPIError(
            str(error), endpoint=ENDPOINT, headers=HEADERS, params=params
        )
    if response.status_code != HTTPStatus.OK:
        raise CustomAPIError(f'Не удалось выполнить запрос. '
                             f'Код ошибки: {response.status_code}',
                             endpoint=ENDPOINT, headers=HEADERS, params=params)
    return response.json()


def check_response(response):
    """Проверка ответа от API."""
    try:
        homeworks = response['homeworks']
        if not isinstance(homeworks, list):
            raise TypeError('Значение ключа "homeworks" не является списком.')
    except KeyError:
        raise KeyError('Ответ API не содержит ключа "homeworks".')
    return homeworks


def parse_status(homework):
    """Статус домашней работы."""
    homework_status = homework.get('status')
    homework_name = homework.get('homework_name')
    if homework_name is None:
        raise KeyError('Ответ API не содержит ключа homework_name')
    if (homework_status not in HOMEWORK_VERDICTS) or (homework_status == ''):
        raise ValueError(f'Отправлен неизвестный статус {homework_status}.')
    verdict = HOMEWORK_VERDICTS[homework_status]
    message = (f'Изменился статус проверки работы "{homework_name}". '
               f'{verdict}')
    return message


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        raise logging.critical(SystemExit)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = date.today()
    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            message = parse_status(homework[0])
            send_message(bot, message)
            logging.info(message)
        except IndexError:
            message = 'Статус не изменился.'
            send_message(bot, message)
            logging.info(message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}.'
            send_message(bot, message)
            logging.error(message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s, %(levelname)s, %(message)s'
    )
    main()
