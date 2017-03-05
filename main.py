#!/usr/bin/python3

import sys
import os
import re
import grab


class ImgsrcParser:

    photo_re = re.compile(r"i='(\d+)',h=(?:i\.charAt\((\d)\)\+)?'(\d)?\.eu\.icdn\.ru',s='/',n='([^']{3})',u='([^']+)'")
    prev_re = re.compile(r"\('left',function\(\) \{window\.location='([^']+)'")
    host = 'http://imgsrc.ru'

    def __init__(self, workdir):
        self.workdir = workdir.rstrip(os.path.sep) + os.path.sep
        self.g = grab.Grab()
        self.g.cookies.set('iamlegal', 'yeah', 'imgsrc.ru')

    def normalize(self, url):
        url = url.split('#')[0]
        if url.startswith('/'):
            url = self.host + url
        return url

    def get_user_photos(self, url):
        d = self.g.go(url)
        elems = d.tree.xpath('//table/tr/td/a[@target="_top"]')
        for elem in elems:
            name = elem.get('href').split('/')[-1].split('.')[0]
            if not name.isalnum():
                print('Bad name:', name)
                continue
            print('\nAlbum', elem.get('href'))
            if not os.path.isdir(self.workdir + name):
                os.mkdir(self.workdir + name)
            self.get_photos(elem.get('href'), self.workdir + name + os.path.sep)

    def get_photos(self, url, workdir=None):
        if workdir is None:
            workdir = self.workdir
        res = []
        url = self.first_photo(url)
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
            res = self.prev_re.search(d.body.decode('utf-8')).group(1)
            if '/user.php' in res:
                break
            print('Previous page:', res)
            url = res
        d = self.g.go(url)
        images = d.tree.xpath('//center/table/tr[@align="center"]/td//img')
        if images[0].get('class') != 'cur':
            ref = d.tree.xpath('//center/table/tr[@align="center"]/td/a')[0]
            url = ref.get('href')
            print('First photo:', url)
        return url

    def get_photo_url(self, body):
        res = self.photo_re.search(body)
        u = res.group(5) + res.group(1) + res.group(4)[1] + res.group(4)[2] + res.group(4)[0]
        cdn = res.group(3) or res.group(1)[int(res.group(2))]
        url = 'http://b' + cdn + '.eu.icdn.ru/' + u[0] + '/' + u + '.jpg'
        return url

    def download_photo(self, url, saveto):
        print('Downloading', url)
        d = self.g.go(url)
        filename = saveto + url.split('/')[-1]
        with open(filename, 'wb') as f:
            f.write(d.body)


def main():
    if len(sys.argv) > 1:
        wd = sys.argv[1]
    else:
        wd = '.'
    if not os.path.isdir(wd):
        os.makedirs(wd)
    parser = ImgsrcParser(wd)
    url = input('Enter url: ')
    if '/user.php' in url:
        parser.get_user_photos(url)
    else:
        parser.get_photos(url)


if __name__ == '__main__':
    main()
