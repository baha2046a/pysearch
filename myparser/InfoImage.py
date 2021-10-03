class InfoImage:
    FILE = "info.txt"

    def __init__(self, url: str, lastUpdate: str, count: str):
        self.url = url
        self.lastUpdate = lastUpdate
        self.count = count
