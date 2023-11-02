class APIRequestError(Exception):
    def __init__(self, message):
        super().__init__(f'Ошибка запроса к API: {message}')

class APIStatusCodeError(Exception):
    def __init__(self, status_code):
        super().__init__(f'Ошибка статус кода API: {status_code}')
