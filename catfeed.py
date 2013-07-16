#!/usr/bin/python
# coding=utf-8

import logging as log
import argparse
import os
import datetime
import time
import urllib
import mimetypes
import BaseHTTPServer
import socket
from operator import attrgetter

VERBOSITY = (
    log.ERROR,
    log.WARNING,
    log.INFO,
    log.DEBUG,
)


class Config:
    __version__ = '0.1'
    __website__ = 'http://github.com/tbienko/catfeed'
    chunk_size = 1024*1024

    # configurable via commandline
    verbosity = 2
    catalog = '.'
    after_download = 'move'
    moveto = 'Downloaded'
    host = 'auto'
    port = '8888'
    title = ''


class FileDescriptor(object):
    path = ""
    name = ""
    date = None
    size = 0

    def __repr__(self):
        return self.name

    @classmethod
    def scan_catalog(self):
        items = []

        for subdir, dirs, files in os.walk(Config.catalog):
            for file in files:
                if Config.after_download == 'move' and \
                        subdir.startswith(Config.moveto):
                    continue

                path = os.path.join(subdir, file)

                (mode, ino, dev, nlink, uid, gid,
                    size, atime, mtime, ctime) = os.stat(path)

                desc = FileDescriptor()
                desc.path = path
                desc.name = os.path.splitext(file)[0]
                desc.date = ctime
                desc.size = size

                items.append(desc)

        return items

    @classmethod
    def get_for_path(self, urlpath):
        for item in FileDescriptor.scan_catalog():
            if item.urlpath == urlpath:
                return item
        return None

    def delete(self):
        log.debug("Deleting: %s", self.path)
        os.remove(self.path)

    def move(self):
        target = os.path.join(Config.moveto, self.relativepath)
        targetdir = os.path.dirname(target)

        log.debug("Moving file from: %s to: %s", self.path, target)

        if not os.path.isdir(targetdir):
            os.makedirs(targetdir)

        os.rename(self.path, target)

    @property
    def relativepath(self):
        return self.path[len(Config.catalog)+1:]

    @property
    def urlpath(self):
        name = self.relativepath
        name = name.replace(' ', '-')
        name = urllib.quote(name)
        return name

    @property
    def mime(self):
        mime = mimetypes.guess_type(self.path)[0]
        return mime if mime is not None else "text/plain"


class CatFeed:

    def setup_argparser(self):
        parser = argparse.ArgumentParser(
            description='Simple feed server for your files. \
                Generate feed for local catalog and download files directly \
                in your favourite podcast player!',
            epilog='Visit ' + Config.__website__ + ' to get the newest \
                script. You can also contribute to this project there.'
        )

        parser.add_argument(
            '-H', '--host', type=str, default=Config.host,
            help='host to start server on (default: ' + Config.host + ')'
        )
        parser.add_argument(
            '-p', '--port', type=int, default=Config.port,
            help='port to start server on (default: ' + Config.port + ')'
        )
        parser.add_argument(
            '-m', '--moveto', type=str, default=Config.moveto, metavar='PATH',
            help='catalog to move downloaded files (absolute or relative path,\
                default: ' + Config.moveto + ')'
        )
        parser.add_argument(
            '-d', '--delete', action='store_true',
            help='remove downloaded files instead of moving to other catalog'
        )
        parser.add_argument(
            '-t', '--title', type=str,
            help='title of feed (default: name of catalog)'
        )
        parser.add_argument(
            '-v', '--verbosity', type=int,
            choices=range(len(VERBOSITY)), default=Config.verbosity,
            help='level of logging (0-ERROR ... 3-DEBUG)'
        )
        parser.add_argument(
            'catalog', type=str,
            help='catalog to generate feed from (absolute or relative path)'
        )

        return parser

    def args_to_config(self, args):
        log.debug("Raw args from  argparse: %s", args)

        # loading arguments to class object

        Config.verbosity = args.verbosity
        log.basicConfig(level=VERBOSITY[Config.verbosity])

        Config.catalog = os.path.abspath(args.catalog)
        log.info("Files will be served from: %s", Config.catalog)

        if args.delete:
            Config.after_download = 'delete'
            log.info("Downloaded files will be deleted")
        else:
            Config.after_download = 'move'

            Config.moveto = self.generate_move_path(args.moveto)
            log.info("Downloaded files will be moved to: %s", Config.moveto)

        if args.host == "auto":
            Config.host = self.find_ip()
            log.info("Host automatically resolved to: %s", Config.host)
        else:
            Config.host = args.host
            log.info("Host set to: %s", Config.host)

        Config.port = args.port
        log.info("Port set to: %s", Config.port)

        if args.title is None:
            Config.title = os.path.basename(Config.catalog)
            log.info("Feed title generated from name of catalog: %s",
                     Config.title)
        else:
            Config.title = args.title
            log.info("Feed title set to: %s", Config.title)

    def find_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("google.com", 80))
            return s.getsockname()[0]
            s.close()
        except:
            return "127.0.0.1"

    def generate_move_path(self, move):
        path = os.path.realpath(move)
        if os.path.isdir(path):
            return path

        return os.path.normpath("%s/%s" % (Config.catalog, move))

    def start_server(self):
        print "Your feed is served on %s" % Feed().feed_url()
        httpd = BaseHTTPServer.HTTPServer((Config.host, Config.port),
                                          RequestHandler)

        try:
            httpd.serve_forever()
        except (KeyboardInterrupt, SystemExit):
            log.info('Stopping...')
        httpd.server_close()

    def __init__(self):
        log.basicConfig(level=VERBOSITY[Config.verbosity],
                        format='[%(levelname)s] %(message)s')

        log.info("Starting CatFeed version %s", Config.__version__)

        parser = self.setup_argparser()
        args = parser.parse_args()
        self.args_to_config(args)

        self.start_server()
        log.info('Stopped.')


class Feed:
    def base_url(self):
        return "http://%s:%s/" % (Config.host, Config.port)

    def feed_url(self):
        return self.base_url()

    def item_url(self, item):
        return self.base_url() + item.urlpath

    def atom_date(self, timestamp):
        return datetime.datetime.fromtimestamp(timestamp).isoformat("T") + "Z"

    def generate_feed(self, items):
        items = sorted(items, key=attrgetter('date'), reverse=True)

        feed = []

        params = {
            'feed': self.feed_url(),
            'base': self.base_url(),
            'title': Config.title,
            'updated': self.atom_date(time.time())
        }

        feed.append("""<feed xmlns="http://www.w3.org/2005/Atom">
                <id>%(feed)s</id>
                <title>%(title)s</title>
                <updated>%(updated)s</updated>
                <link href="%(base)s" />
                <link rel="self" href="%(feed)s" />
                <author>
                    <name>CatFeed</name>
                </author>""" % params)

        for item in items:
            params = {
                'name': item.name,
                'link': self.item_url(item),
                'date': self.atom_date(item.date),
                'mime': item.mime,
                'size': item.size
            }

            feed.append("""
                <entry>
                    <id>%(link)s</id>
                    <title>%(name)s</title>
                    <updated>%(date)s</updated>
                    <link href="%(link)s" />
                    <summary></summary>
                    <link rel="enclosure"
                        type="%(mime)s"
                        title="%(name)s"
                        href="%(link)s"
                        length="%(size)d" />
                </entry>\n""" % params)

        feed.append("</feed>")

        return ''.join(feed)


class RequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.serve(self.path, "HEAD")

    def do_GET(self):
        self.serve(self.path, "GET")

    def serve(self, path, request_type):
        log.debug("New request %s: %s", request_type, self.path)

        if self.path == '/':
            self.serve_feed(request_type)
            return

        item = FileDescriptor.get_for_path(self.path.lstrip('/'))

        if item is not None:
            log.debug("Requested path found")
            self.serve_file(request_type, item)
        else:
            self.serve_404(request_type)

    def serve_404(self, request_type):
        log.debug("Response to %s: %s - 404", request_type, self.path)

        self.send_response(404)
        self.send_header("Content-type", "text/html")
        self.end_headers()

        self.wfile.write("404 Not Found")

    def serve_feed(self, request_type):
        log.debug("Response to %s: %s - Feed", request_type, self.path)

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

        if request_type == 'HEAD':
            return

        items = FileDescriptor.scan_catalog()
        feed = Feed().generate_feed(items)
        self.wfile.write(feed)

    def serve_file(self, request_type, item):
        log.debug("Response to %s: %s - Serving file %s",
                  request_type, self.path, item.path)

        f = open(item.path, 'rb')

        self.send_response(200)
        self.send_header('Content-type', item.mime)
        self.end_headers()

        if request_type == 'HEAD':
            return

        while True:
            chunk = f.read(Config.chunk_size)
            if chunk:
                self.wfile.write(chunk)
            else:
                break

        f.close()

        log.debug("File downloaded: %s", item.path)

        callback = getattr(item, Config.after_download)
        callback()


def main():
    CatFeed()

if __name__ == "__main__":
    main()
