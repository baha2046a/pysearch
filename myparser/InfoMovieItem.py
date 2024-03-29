import json
import shutil
from typing import AnyStr, Tuple, TypeVar, Optional

import aiofiles
import jsons

from MyCommon import async_save_json
from TextOut import TextOut

T = TypeVar('T')


class InfoMovieItem:
    @staticmethod
    def _add(data: dict, name: T, urls=None) -> T:
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
    def _get(data: dict, name: T, urls=None) -> Optional[Tuple[T, dict]]:
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
        return None

    @staticmethod
    def _load(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(e)
            return {}

    @staticmethod
    def _save(path: AnyStr, data) -> None:
        tmp_path = path + "_tmp"
        try:
            d = jsons.dump(data)
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(d, f, ensure_ascii=False, indent=4)
            shutil.move(tmp_path, path)
            TextOut.out(f"Save File: {path}")
        except Exception as e:
            print(e)
        finally:
            f.close()

    @staticmethod
    async def _async_save(path: AnyStr, data) -> None:
        tmp_path = path + "_tmp"
        try:
            TextOut.out(f"Start Save File: {path}")
            d = jsons.dump(data)
            await async_save_json(tmp_path, d)
            shutil.move(tmp_path, path)
            TextOut.out(f"Finish Save File: {path}")
        except Exception as e:
            print(e)

