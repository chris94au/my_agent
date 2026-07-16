from datetime import datetime



def current_time(_):

    return datetime.now().strftime(
        "%d.%m.%Y %H:%M:%S"
    )