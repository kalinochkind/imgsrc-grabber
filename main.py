#!/usr/bin/python3

import sys
import os
import re
import grab


class ImgsrcParser:

    photo_re = re.compile(r"i='(\d+)',h=(?:i\.charAt\((\d)\)\+)?'(\d)?\.eu\.icdn\.ru',s='/',n='([^']{3})',u='([^']+)'")
    host = 'http://imgsrc.ru'

    def __init__(self, workdir):
        self.workdir = workdir.rstrip(os.path.sep) + os.path.sep
        self.g = grab.Grab()
        self.g.cookies.set('iamlegal', 'yeah', 'imgsrc.ru')

    def get_photos(self, url):
        res = []
        while not '/user.php' in url:
            url = url.split('#')[0]
            if url.startswith('/'):
                url = self.host + url
            print('Visiting', url)
            d = self.g.go(url)
            self.download_photo(self.get_photo_url(d.body.decode('utf-8')))
            url = d.tree.get_element_by_id('next_url').get('href')
        print('Finished')

    def get_photo_url(self, body):
        res = self.photo_re.search(body)
        u = res.group(5) + res.group(1) + res.group(4)[1] + res.group(4)[2] + res.group(4)[0]
        cdn = res.group(3) or res.group(1)[int(res.group(2))]
        url = 'http://b' + cdn + '.eu.icdn.ru/' + u[0] + '/' + u + '.jpg'
        return url

    def download_photo(self, url):
        print('Downloading', url)
        d = self.g.go(url)
        filename = self.workdir + url.split('/')[-1]
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
    parser.get_photos(url)


if __name__ == '__main__':
    main()
