import json
import os

from MyCommon import join_path


class InfoImage:
    FILE = "info.txt"

    def __init__(self, url: str, lastUpdate: str, count: str = "-1", folderImage:str = ""):
        self.url = url
        self.lastUpdate = lastUpdate
        self.count = count

    @staticmethod
    def save_info(path, data):
        if data is not None and os.path.isdir(path):
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
                print(info)
                return data
        except Exception as e:
            print(e)
            return None
