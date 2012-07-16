__author__ = 'jakub.zygmunt'
class Validators(object):
    @staticmethod
    def default_validator(value):
        if value is not None and len(value.strip()) > 0:
            return True
        return False
