from notifypy import Notify


class Notification:
    def __init__(self) -> None:
        pass

    @staticmethod
    def send(title: str, text: str, icon: str):
        notification = Notify()
        notification.title = title
        notification.icon = icon
        notification.message = text
        notification.send()
