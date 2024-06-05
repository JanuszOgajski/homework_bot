class MissingVariableError(SystemExit):
    """Программа завершит работу если нет переменной в .env."""

    pass


class EmptyResponseAPIError(Exception):
    """Ответ API пуст."""

    pass


class APIError(Exception):
    """Выбрасывается если статус ответа не 200."""

    pass
