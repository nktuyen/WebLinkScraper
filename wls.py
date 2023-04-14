import sys
import os
import re
import json
import bs4
import enum
import requests
import concurrent.futures
from threading import Lock
import multiprocessing

class Option:
    def __init__(self, keyword: str, type = str, required: bool = False, desc: str = '', default_value = None, allow_values: list = None, allow_none: bool = False) -> None:
        self._key = keyword
        self._type = type
        self._required: bool = required
        self._desc = desc
        self._allow_values: list = allow_values
        self._has_value: bool = False
        self._value = None
        self._defval = default_value
        self._allow_none: bool = allow_none
    
    @property
    def keyword(self) -> str:
        return self._key
    
    @keyword.setter
    def keywork(self, val: str):
        set.__weakrefoffset__ = val

    @property
    def type(self) :
        return self._type
    
    @type.setter
    def type(self, type):
        self._type = type

    @property
    def required(self) -> bool:
        return self._required
    
    @required.setter
    def required(self, val: bool):
        self._required = val

    @property
    def description(self) -> str:
        return self._desc
    
    @description.setter
    def description(self, val: str):
        self._desc = val

    @property
    def default_value(self):
        return self._defval
    
    @default_value.setter
    def default_value(self, val):
        self._defval = val

    @property
    def allow_values(self) -> list:
        return self._allow_values
    
    @allow_values.setter
    def allow_values(self, vals: list):
        self._allow_values = vals

    @property
    def value(self):
        return self._value
    
    @value.setter
    def value(self, val):
        self._value = val
        self._has_value = True

    @property
    def has_value(self) -> bool:
        return self._has_value

    def help_string(self, left_width: int = 20) -> str:
        left: str = '{string:{width}}'.format(string=self._key, width=left_width)
        return f'{left}: {self._desc}'
    
    def value_string(self, left_width: int = 20) -> str:
        left: str = '{string:{width}}'.format(string=self._key, width=left_width)
        return f'{left}: {self._value}'
    
    def reset(self):
        self._value = None
        self._has_value = False
    
    def _internal_validate(self, val: str):
        if (val is None) and (not self._allow_none):
            return None
        if self._allow_values is not None:
            for vv in self._allow_values:
                if val == vv:
                    return vv
        return val
    
    def __str__(self) -> str:
        return self._key
    
    def validate(self, value: str) -> bool:
        validated_value = self._internal_validate(value)
        if validated_value is None:
            return False
        self.value = validated_value
        return True
    
class BooleanOption(Option):
    def __init__(self, keyword: str, required: bool = False, desc: str = '', defval: bool = False) -> None:
        super().__init__(keyword, bool, required, desc, defval,  [True, False, 0, 1, 'True', 'False', '0', '1', 'Yes', 'No'])

    def _internal_validate(self, val: str) -> bool:
        return super()._internal_validate(val)
    
class IntegerOption(Option):
    def __init__(self, keyword: str, required: bool = False, desc: str = '', defval: int = 0, allow_values: list = None) -> None:
        super().__init__(keyword, int, required, desc, defval, allow_values)

    def _internal_validate(self, val: str) -> int:
        return super()._internal_validate(val)

class StringOption(Option):
    def __init__(self, keyword: str, required: bool = False, desc: str = '', defval: str = '', allow_values: list = None) -> None:
        super().__init__(keyword, str, required, desc, defval, allow_values)
    
    def _internal_validate(self, val: str) -> str:
        if not isinstance(val, str):
            return None
        return super()._internal_validate(val)
    

def url_validate(url: str) -> bool:
        if not isinstance(url, str):
            return False
        if url.upper().startswith('http://'.upper()):
            url = url[len('http://'):]
        elif url.upper().startswith('https://'.upper()):
            url = url[len('https://'):]
        if url.upper().startswith('http://www.'.upper()):
            url = url[len('http://www.'):]
        elif url.upper().startswith('https://www.'.upper()):
            url = url[len('https://www.'):]
        elif url.upper().startswith('www.'.upper()):
            url = url[len('www.'):]
        if url.endswith('/'):
            url = url[:-1]
        tmp: list = url.split('/')
        url = tmp[0]
        ls: list = url.split('.')
        if len(ls) < 2:
            return False
        if len(ls) > 4:
            return False
        name: str = ''
        ch: str = ''
        valids: list = ['_', '-']
        for name in ls:
            if len(name) <= 0:
                return False
            ch = name[0:1]
            if not ch.isalnum() and ch not in valids:
                return False
        host: str = ls[0]
        for ch in host:
            if not ch.isalnum() and ch not in valids:
                return False
        return True

def url_root(url: str) -> str:
    if not isinstance(url, str):
        return ''
    scheme: str = ''
    if url.upper().startswith('http://www.'.upper()):
        url = url[len('http://www.'):]
        scheme = 'http://www.'
    elif url.upper().startswith('https://www.'.upper()):
        url = url[len('https://www.'):]
        scheme = 'https://www.'
    elif url.upper().startswith('http://'.upper()):
        url = url[len('http://'):]
        scheme = 'http://'
    elif url.upper().startswith('https://'.upper()):
        url = url[len('https://'):]
        scheme = 'https://'
    elif url.upper().startswith('www.'.upper()):
        url = url[len('www.'):]
        scheme = 'www.'
    url = url.rstrip('/').lstrip('/')
    tmp: list = url.split('/')
    url = tmp[0].rstrip('/').lstrip('/')
    return f'{scheme}{url}'
    
def url_hostname(url: str) -> str:
    if not isinstance(url, str):
        return ''
    scheme: str = ''
    if url.upper().startswith('http://www.'.upper()):
        url = url[len('http://www.'):]
        scheme = 'http://www.'
    elif url.upper().startswith('https://www.'.upper()):
        url = url[len('https://www.'):]
        scheme = 'https://www.'
    elif url.upper().startswith('http://'.upper()):
        url = url[len('http://'):]
        scheme = 'http://'
    elif url.upper().startswith('https://'.upper()):
        url = url[len('https://'):]
        scheme = 'https://'
    elif url.upper().startswith('www.'.upper()):
        url = url[len('www.'):]
        scheme = 'www.'
    url = url.rstrip('/').lstrip('/')
    tmp: list = url.split('/')
    url = tmp[0].rstrip('/').lstrip('/')
    return url

def parse_url(arg: tuple) -> dict: #Return number of parsed words
    if arg is None:
        return None
    url: str = arg[0]
    fork: bool = arg[1]
    if len(arg) > 2:
        url_words: dict = arg[2]
        if url_words is None:
            url_words: dict = {}
    else:
        url_words: dict = {}    

    dictionary: enchant.Dict = None
    if len(arg) > 3:
        dictionary = arg[3]
        if dictionary is None:
            dictionary = enchant.Dict("en_US")
    else:
        dictionary = enchant.Dict("en_US")

    file: str = None
    if len(arg) > 4:
        file = arg[4]
    
    locker: Lock = None
    if len(arg) > 5:
        locker = arg[5]
        if locker is None:
            locker = Lock()
    else:
        locker = Lock()
    
    if url is None or not isinstance(url, str):
        return url_words
    
    words: dict = None
    if url in url_words:
        words = url_words[url]
    else:
        words = {}
        url_words[url] = words
    
    print(f'Parsing {url}...')
    res: requests.Response = None
    try:
        res = requests.get(url, timeout=5)
    except Exception as ex:
        print(f'Exception:{ex}')
        return url_words
    
    if res.status_code != 200:
        return url_words
    if res.text is None or len(res.text) <= 0:
        return url_words
    
    parser: bs4.BeautifulSoup = bs4.BeautifulSoup(res.text, 'html.parser')    
    text: str = parser.get_text()
    if text is None or len(text) <= 0:
        return words
    text = text.lstrip().rstrip()
    texts: list = text.split()
    w: str = ''
    for w in texts:
        if not w.isalpha():
            continue
        if not dictionary.check(w):
            continue
        for ww in [w.lower(), w.upper(), w.capitalize()]:
            if ww in words:
                words[ww] += 1
            else:
                words[ww] = 1
    if file is not None:
        try:
            with locker:
                with open(f'{url_hostname(url)}.{file}','w') as json_file:
                    json_file.write(json.dumps(url_words, sort_keys=True, indent=4))
        except Exception as ex:
            #print(f'Cannot save words to {_output.value} due to error:{ex}')
            #print(url_words)
            #exit(0)
            pass
    if fork:
        for anchor in parser.find_all('a'):
            link: str = None
            try:
                link = anchor['href']
            except:
                link = None
            if link is None:
                continue
            link = link.rstrip('/')
            my_root: str = url_root(url)
            if (not link.upper().startswith('http://'.upper())) and (not  link.upper().startswith('https://'.upper())) and (not  link.upper().startswith('www.'.upper())):
                link = link.lstrip('/')
                if link in ['#', '?']:
                    link = ''
                link = f'{my_root}/{link}'.rstrip('/')
            your_root: str = url_root(link)
            if my_root.upper() == your_root.upper():
                if url != link and link not in url_words:
                    url_words[link] = {}
                    uws = parse_url((link, fork, url_words, dictionary, file, locker))
                    if uws is not None:
                        url_words = url_words | uws
    return url_words

if __name__=="__main__":
    _verbose: BooleanOption = BooleanOption("--verbose", "Verbose output", True)
    _fork: BooleanOption = BooleanOption("--fork", "Also parse any encountered link", True)
    _input: StringOption = StringOption("--in", True, "Input file which contains words will be merged with results", None)
    _output: StringOption = StringOption("--out", "Output file name", None)

    option_list : list = [
        _verbose,
        _fork,
        _input,
        _output
    ]
    def usage():
        print(f'Usage: {os.path.basename(sys.argv[0])} [options] urls')
        print('  [options]')
        for opt in option_list:
            print(f'  {opt.help_string()}')
    
    if len(sys.argv) < 2:
        usage()
        exit(0)

    opt: Option = None
    arg: str = ''
    urls: list = []
    
    for index in range(1, len(sys.argv)):
        arg = sys.argv[index]
        for opt in option_list:
            if arg.upper() == opt.keyword.upper():
                if opt.validate(opt.default_value):
                    arg = None
                    break
                else:
                    print(f'Invalid value specified for {opt.keyword}:{opt.default_value}')
                    exit(1)
            elif arg.upper().startswith(f'{opt.keyword.upper()}='):
                arg_val: str = arg[len(opt.keyword) + len('='):]
                if opt.validate(arg_val):
                    arg = None
                    break
                else:
                    print(f'Invalid value specified for {opt.keyword}:{arg_val}')
                    exit(1)                
        if arg is not None:
            if url_validate(arg):
                urls.append(url_root(arg))
            else:
                print(f'Invalid url:{arg}')
                exit(1)
    
    if _verbose.has_value and _verbose.value == True:
        has_opt: bool = False
        for opt in option_list:
            if opt.has_value:
                has_opt = True
                print(f'  {opt.value_string()}')
        if has_opt:
            print()

    url_words: dict = {}
    if _input.has_value and os.path.exists(_input.value):
        try:
            with open(_output.value,'r+') as json_file: 
                obj = json.load(json_file)
                if obj:
                    url_words = obj
        except Exception as ex:
            print(f'Cannot open input file:{_input.value}')
            #exit(1)
    dictionary: enchant.Dict = None
    if _language.has_value:
        dictionary = enchant.Dict(_language.value)
    else:
        dictionary = enchant.Dict("en_US")
    urls = set(url_words.keys()) ^ set(urls)
    manager: multiprocessing.Manager = multiprocessing.Manager()
    locker: multiprocessing.Lock = manager.Lock()
    with concurrent.futures.ProcessPoolExecutor(max_workers=max(2,min(61, len(urls)))) as executor:
        futures = { executor.submit(parse_url, (url, _fork.value if _fork.has_value else False, url_words, dictionary, _output.value if _output.has_value else None, locker)) : url for url in urls}
        url: str = ''
        for future in concurrent.futures.as_completed(futures):
            #url = futures[future]
            uws = future.result()
            if uws is None:
                print(f'Parsed url {url} failed')
            else:
                url_words = url_words | uws
                if _output.has_value and len(_output.value) > 0:
                    try:
                        with open(_output.value,'w') as json_file:
                            json_file.write(json.dumps(url_words, sort_keys=True, indent=4))
                    except Exception as ex:
                        print(f'Cannot save words to {_output.value} due to error:{ex}')
                        print(url_words)
                        #exit(0)