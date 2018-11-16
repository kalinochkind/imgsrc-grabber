#!/usr/bin/env python3

import sys
import os
import re
import grab
import time


def get_argument(s, variables):
    arg = s.split('(')[1].split(')')[0]
    if "'" in arg:
        return arg.strip("'")
    elif arg.isdigit():
        return int(arg)
    elif arg in variables:
        return variables[arg]
    else:
        return exec_js(arg, variables)

def eval_js(val, variables):
    evaluated = []
    for i in val:
        if i.startswith("'"):
            evaluated.append(i[1:-1])
        elif i.startswith('document.getElementById('):
            evaluated.append(variables['_url'])
        elif '.lastIndexOf' in i:
            varname = i.split('.')[0]
            substr = get_argument(i, variables)
            evaluated.append(variables[varname].rfind(substr))
        elif '.indexOf' in i:
            varname = i.split('.')[0]
            substr = get_argument(i, variables)
            evaluated.append(variables[varname].find(substr))
        elif '.slice' in i:
            varname = i.split('.')[0]
            bounds = [exec_js(j, variables) for j in i.split('(')[1].split(')')[0].split(',')]
            evaluated.append(variables[varname][bounds[0]:bounds[1]])
        elif '.charAt' in i:
            varname = i.split('.')[0]
            idx = i.split('(')[1].split(')')[0]
            idx = exec_js(idx, variables)
            evaluated.append(variables[varname][idx])
        elif '[' in i:
            varname = i.split('[')[0]
            idx = i.split('[')[1].rstrip(']')
            if idx.isalpha():
                idx = variables[idx]
            evaluated.append(variables[varname][int(idx)])
        elif i.isalpha():
            evaluated.append(variables[i])
        elif i.startswith('String.fromCharCode(') or i.startswith('String.fromCodePoint('):
            num = get_argument(i, variables)
            evaluated.append(chr(num))
        else:
            evaluated.append(int(i))
    if isinstance(evaluated[0], str):
        return ''.join(evaluated)
    else:
        return sum(evaluated)

def exec_js(val, variables):
    val = list(filter(bool, val.replace('-', '+-').split('+')))
    l = []
    for i in val:
        if l and l[-1].count('(') > l[-1].count(')'):
            l[-1] += '+' + i
        else:
            l.append(i)
    return eval_js(l, variables)

class ImgsrcParser:

    photo_re = re.compile(r" class='cur' src='(https?://[^']+)'")
    photo_re = re.compile(r"<a href='#bp'><img src='(https?://[^']+)' id=")
    photo_js_re = re.compile(r"var ((?:[a-z]+=[^;]*)+);", re.DOTALL)
    photo_result_re = re.compile(r"^[a-z]\.src=([^;]+);", re.MULTILINE)
    iamlegal_re = re.compile(r"<a href='(/main/warn.php\?[^']+)'>")
    prev_re = re.compile(r"\('left',function\(\) \{window\.location='([^']+)'")
    host = 'http://imgsrc.ru'

    def __init__(self, workdir):
        self.workdir = workdir.rstrip(os.path.sep) + os.path.sep
        self.g = grab.Grab()
        self.g.cookies.set(name='iamlegal', value='yeah', domain='.imgsrc.ru', path='/', expires=time.time()+3600*24)
        self.g.go(self.host)

    def normalize(self, url):
        url = url.split('#')[0]
        if url.startswith('/'):
            url = self.host + url
        return url

    def pass_preword(self, url):
        d = self.g.go(url)
        body = d.body.decode('utf-8')
        legal = self.iamlegal_re.search(body)
        if legal:
            url = legal.group(1)
            print('\nIamlegal', url, end='')
            d = self.g.go(url)
        return d.tree.xpath('//center//table/tr[@align="center"]/td[@align="left"]/form')[0].get('action')

    def get_user_photos(self, url):
        d = self.g.go(url)
        elems = d.tree.xpath('//table/tr/td/a[@target="_top"]')
        for elem in elems:
            album = self.normalize(elem.get('href'))

            if '/preword.php' in album:
                print('\nPreword', album, end='')
                name = 'a' + album.split('=')[-1]
                album = self.pass_preword(album)
            else:
                name = album.split('/')[-1].split('.')[0]
            if '/passchk.php' in album:
                print('\nLocked', album)
                continue
            if not name.isalnum():
                print('\nBad name:', name)
                continue
            print('\nAlbum', album)
            if not os.path.isdir(self.workdir + name):
                os.mkdir(self.workdir + name)
            self.get_photos(album, self.workdir + name + os.path.sep)

    def get_photos(self, url, workdir=None):
        if workdir is None:
            workdir = self.workdir
        res = []
        url = self.first_photo(url)
        with open(workdir + '.imgsrc', 'w') as f:
            print(url, file=f)
        while not '/user.php' in url:
            url = self.normalize(url)
            print('Visiting', url)
            d = self.g.go(url)
            self.download_photo(self.get_photo_url(d.body.decode('utf-8')), workdir)
            url = d.tree.get_element_by_id('next_url').get('href')
        print('Finished')

    def first_photo(self, url):
        while True:
            url = self.normalize(url)
            d = self.g.go(url)
            res = self.prev_re.search(d.body.decode('utf-8'))
            if not res:
                url = self.pass_preword(url)
                if not url:
                    return None
                continue
            res = res.group(1)
            if '/user.php' in res:
                break
            print('Previous page:', res)
            url = res
        d = self.g.go(url)
        images = d.tree.xpath('//table[@class="pret"]//tr/td')
        if images[0].get('class') != 'curt':
            ref = d.tree.xpath('//table[@class="pret"]//tr/td//a')[0]
            url = ref.get('href')
            print('First photo:', url)
        return url

    def get_photo_url(self, body):
        js = [i.rstrip(',') for i in sum([x.splitlines() for x in self.photo_js_re.findall(body)], [])]
        js = sum([i.split(', ') for i in js], [])
        answer = self.photo_result_re.search(body).group(1)
        variables = {'_url': self.photo_re.search(body).group(1)}
        for cmd in js:
            name, val = cmd.split('=')
            result = exec_js(val, variables)
            variables[name] = result
        return eval_js(answer.replace('-', '+-').split('+'), variables)

    def download_photo(self, url, saveto):
        print('Downloading', url)
        d = self.g.go(url)
        filename = saveto + url.split('/')[-1]
        with open(filename, 'wb') as f:
            f.write(d.body)


def get_args(args):
    wd = url = None
    for i in args:
        if i.startswith('http://') or i.startswith('https://'):
            if not url:
                url = i
        elif not wd:
            wd = i
    while not url:
        url = input('Enter url: ')
    while not wd:
        wd = input('Where to save: ')
    return wd, url

def main():
    wd, url = get_args(sys.argv[1:])
    if not os.path.isdir(wd):
        os.makedirs(wd)
    parser = ImgsrcParser(wd)
    if '/user.php' in url:
        parser.get_user_photos(url)
    else:
        parser.get_photos(url)


if __name__ == '__main__':
    main()
