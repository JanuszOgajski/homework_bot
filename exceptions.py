class MissingVariableError(SystemExit):
    """Программа завершит работу если нет переменной в .env."""


class EmptyResponseAPIError(Exception):
    """Ответ API пуст."""


class APIError(Exception):
    """Выбрасывается если статус ответа не 200."""


class APIRequestError(Exception):
    """Ошибка поднимаемая под RequestException."""
