import json
import os

from MyCommon import join_path


class InfoImage:
    FILE = "info.txt"

    def __init__(self, url: str, lastUpdate: str, count: int = -1, folderImage:str = ""):
        self.url = url
        self.lastUpdate = lastUpdate
        self.count = count

    @staticmethod
    def update_count(path, count):
        info = InfoImage.load_info(path)
        if info is not None:
            info.count = count
            InfoImage.save_info(path, info)

    @staticmethod
    def save_info(path, data):
        if data is not None and os.path.isdir(path):
            if isinstance(data, InfoImage):
                data = data.__dict__

            info_path = join_path(path, InfoImage.FILE)
            try:
                with open(info_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
            except Exception as e:
                print(e)
            finally:
                f.close()

    @staticmethod
    def load_info(path):
        info_path = join_path(path, InfoImage.FILE)
        try:
            with open(info_path, encoding="utf-8") as f:
                data = json.load(f)
                info = InfoImage(**data)
                print(data)
                return info
        except Exception as e:
            print(e)
            return None
