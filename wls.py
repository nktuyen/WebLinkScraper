import sys
import os
import re
import bs4
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

    def print_help(self, indent: int = 0, left_width: int = 21):
        desc_list: list = self._desc.split('\n')
        left_width = max(0, left_width)
        indent = max(0, indent)
        left: str = '{string:{width}}'.format(string=f'{self._key} {"(Required)" if self._required else "[Optional]"}', width=left_width)
        print(f'{" " * indent}{left}: {desc_list[0]}')
        if len(desc_list) > 1:
            for idx in range(1, len(desc_list)):
                desc: str = desc_list[idx]
                print(f'{" " * (indent + left_width)}: {desc}')
    
    def print_keyvalue(self, indent: int = 0, left_width: int = 12) -> str:
        indent = max(0, indent)
        left_width = max(0, left_width)
        left: str = '{string:{width}}'.format(string=self._key, width=left_width)
        print(f'{" " * indent}{left}: {self._value}')
    
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
    

def url_validate(input_url: str, browse: bool = False) -> bool:
        if not isinstance(input_url, str):
            return False
        url: str = input_url
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

        if browse:
            res: requests.Response = None
            headers = requests.utils.default_headers()
            headers.update(
                {
                    'User-Agent': 'Mozilla/5.0',
                }
            )
            try:
                res = requests.get(input_url, timeout=5, allow_redirects=False)
            except requests.ConnectionError:
                res = requests.get(input_url, timeout=5, headers=headers, allow_redirects=False)
            except Exception as ex:
                print(f'Exception:{ex}')
                return False
            
            if res.status_code != 200:
                return False
            if 'text/html' not in res.headers['content-type']:
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
    url = f'{scheme}{url}'

    return url
    
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

def parse_links(arg: tuple) -> set:
    if arg is None:
        return {}
    url: str = arg[0]
    fork: bool = arg[1] 

    urls: set = None
    if len(arg) > 2:
        urls = arg[2]
    if not isinstance(urls, set):
        urls = set()
    
    file: str = None
    if len(arg) > 3:
        file = arg[3]
    
    locker: Lock = None
    if len(arg) > 4:
        locker = arg[4]
        if locker is None:
            locker = multiprocessing.Manager().Lock()
    else:
        locker = multiprocessing.Manager().Lock()

    _domain_tree_only: bool = False
    if len(arg) > 5:
        _domain_tree_only = arg[5]
        if _domain_tree_only is None:
            _domain_tree_only = False

    if url is None or not isinstance(url, str):
        return urls
    if url not in urls:
        with locker:
            urls.add(url)
    res: requests.Response = None
    headers = requests.utils.default_headers()
    headers.update(
        {
            'User-Agent': 'Mozilla/5.0',
        }
    )
    try:
        res = requests.get(url, timeout=5, allow_redirects=False)
    except requests.ConnectionError as err:
        try:
            res = requests.get(url, timeout=5, headers=headers, allow_redirects=False)
        except Exception as ex2:
            if _verbose:
                print(f'Exception:{ex2}')
    except Exception as ex:
        print(f'Exception:{ex}')
        return urls
    
    if res.status_code != 200:
        return urls

    content_type: str =  'text/html'
    if 'content-type' in res.headers:
        content_type =  res.headers['content-type']
        if content_type.find('text/html') == -1:
            return urls
        
    if res.text is None or len(res.text) <= 0:
        return urls
    
    parser: bs4.BeautifulSoup = bs4.BeautifulSoup(res.text, 'html.parser')    
    anchors = parser.find_all('a')
    link: str = None
    if anchors is None:
        return urls
    for a in anchors:
        try:
            link = a['href']
        except:
            link = None
        if link is None:
            continue
        my_root: str = url
        pos: int = -1
        pos_list: list = []
        for ch in ['?', '#']:
            pos = url.find(ch)
            if pos != -1:
                pos_list.append(pos)
        if len(pos_list) > 0:
            pos = min(pos_list)
            my_root = url[:pos]
        my_root = my_root.rsplit('/')
        link = link.strip()
        if (not link.upper().startswith('http://'.upper())) and (not  link.upper().startswith('https://'.upper())) and (not  link.upper().startswith('www.'.upper())):
            if link.startswith('#'):
                continue
            link = f'{my_root}/{link.lstrip("/")}'.rstrip('/')
        link = link.rstrip('/')
        if not url_validate(link):
            print(f'{link}[Invalid]')
            continue

        if _domain_tree_only:
            my_root: str = url_root(url)
            if not link.upper().startswith(my_root.upper()):
                print(f'{link}[OtherDomain]')
                continue

        with locker:
            if link in urls:
                print(f'{link}[Ignored]')
                continue
            urls.add(link)
            print(f'{link}[Accepted]')
        
        if file is not None:
            try:
                with locker:
                    with open(file,'a') as txt_file:
                        txt_file.write(f'{link}\n')
            except Exception as ex:
                pass
        
        if fork:
            urls |= parse_links((link, fork, urls, file, locker, _domain_tree_only))
    return urls

if __name__=="__main__":
    _verbose: BooleanOption = BooleanOption("--verbose", False, "Verbose output", True)
    _fork: BooleanOption = BooleanOption("--fork", False, "Also browse any encountered link", True)
    _exclude: StringOption = StringOption("--exclude", False, "Input file which contains list of URL(s) will be excluded", None)
    _output: StringOption = StringOption("--output", False, "Output file which parsed URL(s) will be written to", None)
    _update: BooleanOption = BooleanOption("--update", False, f'Update mode\nWhen {_output.keyword} is specified\nFound URL(s) will be appended to output file', True)
    _domain_tree: BooleanOption = BooleanOption("--domain-tree", False, "Only browse URL(s) in the same domain tree", False)

    option_list : list = [
        _verbose,
        _fork,
        _exclude,
        _output,
        _update,
        _domain_tree
    ]
    def usage(indent: int = 2, left_width: int = 21):
        print(f'Usage: {os.path.basename(sys.argv[0])} [OPTIONS] urls')
        print('{}{string:{width}}: URL(s) to browse'.format(" " * indent, string='URLS', width=left_width))
        print('  [OPTIONS]')
        for opt in option_list:
            opt.print_help(2)
    
    if len(sys.argv) < 2:
        usage()
        exit(0)

    opt: Option = None
    arg: str = ''
    specified_urls: set = set()
    
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
                specified_urls.add(arg.rstrip('/'))
            else:
                print(f'Invalid url:{arg}')
                exit(1)

    if len(specified_urls) <= 0:
        print('No URL specified')
        exit(1)
        
    require_reinput: bool = False
    for opt in option_list:
        if opt.required and not opt.has_value:
            require_reinput = True
            print(f'{opt.keyword} is mandatory but not specified')
    if require_reinput:
        exit(1)
    
    if _verbose.has_value and _verbose.value == True:
        has_opt: bool = False
        for opt in option_list:
            if opt.has_value:
                has_opt = True
                break
        if has_opt:
            print(f'  [OPTIONS]')
            for opt in option_list:
                if opt.has_value:
                    opt.print_keyvalue(2)
            print()
    ignore_urls: set = set()
    if _exclude.has_value and os.path.exists(_exclude.value):
        try:
            with open(_exclude.value,'r') as txt_file: 
                line: str = txt_file.readline()
                while line:
                    line = line.strip().rstrip('/')
                    if url_validate(line):
                        if line not in ignore_urls:
                            ignore_urls.add(line)
                    else:
                        print(f'[W]:url is not valid:{line}')
                    line = txt_file.readline()
        except Exception as ex:
            print(f'Cannot open file:{_exclude.value}')
            exit(1)

    if _update.has_value and _output.has_value and _update.value == False:
        if os.path.exists(_output.value):
            try:
                os.remove(_output.value)
            except Exception as ex:
                print(f'Cannot remove existing file:{_output.value}')
                exit(1)
    
    manager: multiprocessing.Manager = multiprocessing.Manager()
    locker: multiprocessing.Lock = manager.Lock()
    with concurrent.futures.ProcessPoolExecutor(max_workers=max(2,min(61, len(specified_urls)))) as executor:
        futures = { executor.submit(parse_links, (url, _fork.value if _fork.has_value else False, ignore_urls, _output.value if _output.has_value else None, locker, _domain_tree.value if _domain_tree.has_value else False)) : url for url in specified_urls}
        url: str = ''
        for future in concurrent.futures.as_completed(futures):
            url = futures[future]
            urls = future.result()
            if url:
                if _output.has_value:
                    try:
                        with locker:
                            with open(f'{_output.value}','a') as txt_file:
                                txt_file.write(f'{url}\n')
                    except Exception as ex:
                        print(url)
                else:
                    with locker:
                        print(url)