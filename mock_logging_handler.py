import logging

class MockLoggingHandler(logging.Handler):
    """Mock logging hanlder to check for expected logs. from StackOverflow
        http://stackoverflow.com/a/1049375"""

    def __init__(self, *args, **kwargs):
        self.reset()
        logging.Handler.__init__(self, *args, **kwargs)

    def emit(self, record):
        self.messages[record.levelname.lower()].append(record.getMessage())

    def reset(self):
        self.messages = {
            'debug': [],
            'info': [],
            'warning': [],
            'error': [],
            'critical': [],
            }