import json


class InfoMovieItem:
    @staticmethod
    def _add(data, name, urls=None):
        if name:
            if name in data:
                if urls:
                    data[name].update(urls)
            else:
                if urls:
                    data[name] = urls
                else:
                    data[name] = {}
        return name

    @staticmethod
    def _get(data, name, urls=None):
        if name:
            if name in data:
                if urls:
                    data[name].update(urls)
            else:
                if urls:
                    data[name] = urls
                else:
                    data[name] = {}
            return name, data[name]
        return None, {}

    @staticmethod
    def _load(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(e)
            return {}

    @staticmethod
    def _save(path, data):
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(e)
        finally:
            f.close()