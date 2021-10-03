import json
from datetime import date


class MyEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, date):
            return {'_type': 'date', 'value': o.toordinal()}
        #if isinstance(o, InfoImage):
        #    return {'_type': 'MyA', 'value': o.__dict__}
        return json.JSONEncoder.default(self, o)


class MyDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(self, object_hook=self.object_hook,
                                  *args, **kwargs)

    def object_hook(self, o):
        if '_type' not in o:
            return o
        o_type = o['_type']
        if o_type == 'date':
            return date.fromordinal(o['value'])
        #elif o_type == 'MyA':
        #    return MyA(**o['value'])
