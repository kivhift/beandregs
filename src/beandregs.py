#!/usr/bin/env python3
#
# Copyright (c) 2012, 2019 Joshua Hughes <kivhift@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#

import argparse
import atexit
import configparser
import datetime
import io
import logging
import os
import re
import shutil
import sys
import time

import PIL.Image
import requests

__version__ = '1.2.0'

_logger = logging.getLogger(__name__)
_defaults = dict(
    width = 300
    , height = 300
    , outdir = 'beandregs-output'
    , resize_dir = 'beandregs-output/resized'
    , log_file = 'beandregs-output/images.log'
)

def get_image_and_resize(url, width, height, basename, resize_dir = None):
    ext = os.path.splitext(url)[1].lower()
    resized = basename + ext
    h, t = os.path.split(basename)
    orig = os.path.join(h, 'orig-' + t + ext)
    if os.path.exists(orig):
        _logger.debug(f'{orig} already exists, clobbering')

    if os.path.exists(url):
        _logger.debug(f'Copying local file {url} to {orig}')
        shutil.copy2(url, orig)
    else:
        with requests.get(url) as r:
            if not r.ok:
                _logger.error(
                    f'Could not get {url}: {r.status_code} {r.reason}')
                return
            with open(orig, 'w+b') as f:
                f.write(r.content)

    with PIL.Image.open(orig) as im:
        w, h = im.size
        resize_not_needed = w <= width and h <= height
        if not resize_not_needed:
            _logger.debug(f'Resizing {orig} to {resized}')
            im.thumbnail((width, height), PIL.Image.ANTIALIAS)
            im.save(resized)

    if resize_not_needed:
        if os.path.exists(resized):
            _logger.debug(f'{resized} already exists, removing')
            os.remove(resized)
        _logger.debug(f'Resize not needed; renaming {orig} to {resized}')
        os.rename(orig, resized)

    if resize_dir:
        absor = os.path.realpath(resized)
        absnr = os.path.realpath(os.path.join(
            resize_dir, os.path.basename(resized)))
        if absor != absnr:
            shutil.copy2(resized, resize_dir)
            _logger.debug(f'Copied {resized} to {resize_dir}')

class Cfg:
    def __init__(self):
        for k in _defaults:
            setattr(self, k, _defaults[k])

    def __str__(self):
        s = []
        _a = s.append
        for k in self.__dict__:
            _a(f'{k} = {getattr(self, k)}')
        return '\n'.join(s)

def load_config(cfg_file = None):
    cfg = Cfg()
    if cfg_file:
        _logger.debug(f'Load config file: {cfg_file}')
        tmp = configparser.ConfigParser()
        tmp.read(cfg_file)
        sec = tmp['beandregs']
        for k in _defaults:
            if k in sec:
                setattr(cfg, k, sec[k])

    return cfg

def image_locations(ims):
    with ims if isinstance(ims, io.TextIOBase) else open(
            ims, 'r', encoding = 'utf-8') as inf:
        for ln in inf:
            ln = re.sub(r'#.*$', '', ln)
            if '' == ln or ln.isspace(): continue
            yield [ x.strip() for x in ln.split('=', 1) ]

def _setup_logging(debug = False):
    L = logging.getLogger('')
    L.setLevel(logging.DEBUG)

    fh = logging.FileHandler(
        filename = os.path.join(os.curdir, 'beandregs.log')
        , encoding = 'utf-8')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(' ][ '.join('''
        %(asctime)s
        %(levelname).1s
        %(message)s
        '''.split())))
    L.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG if debug else logging.INFO)
    ch.setFormatter(logging.Formatter('%(message)s'))
    L.addHandler(ch)

    L.debug(f'** Start beandregs v{__version__} logging.')
    atexit.register(L.debug, '** Stop beandregs')

def ISO_8601_time_stamp():
    offset = time.altzone if time.localtime().tm_isdst else time.timezone
    delta = datetime.timedelta(seconds = -offset)
    now = datetime.datetime.now()
    return now.replace(tzinfo = datetime.timezone(offset = delta)).isoformat()

def main(args_list = None):
    arg_parser = argparse.ArgumentParser(
        description = 'Retrieve and (possibly) resize images')
    _a = arg_parser.add_argument
    _a('-i', '--images', default = sys.stdin
        , help = 'Image-location file to use [default: stdin]')
    _a('-l', '--log', dest = 'log_file', default = None
        , help = 'File to log to (for possible redownloading, etc)')
    _a('-c', '--config'
        , help = 'Configuration file to use')
    _a('-o', '--output-dir', dest = 'outdir'
        , help = 'Directory to use for image output'
            f' [default: {_defaults["outdir"]}]')
    _a('-r', '--resize-dir'
        , help = 'Directory to use for resized-image output'
            f' [default: {_defaults["resize_dir"]}]')
    _a('-W', '--width', type = int
        , help = f'Width to resize to [default: {_defaults["width"]}]')
    _a('-H', '--height', type = int
        , help = f'Height to resize to [default: {_defaults["height"]}]')
    _a('-d', '--debug', action = 'store_true'
        , help = 'Send all logging output to console')

    args = arg_parser.parse_args(args_list or sys.argv[1:])

    _setup_logging(args.debug)
    cfg = load_config(args.config)

    # Make command line take precedence over config file.
    cfg.height = int(args.height or cfg.height)
    cfg.log_file = args.log_file or cfg.log_file
    cfg.outdir = os.path.expanduser(args.outdir or cfg.outdir)
    cfg.resize_dir = os.path.expanduser(args.resize_dir or cfg.resize_dir)
    cfg.width = int(args.width or cfg.width)

    if not os.path.exists(cfg.outdir):
        _logger.debug(f'Creating output directory: {cfg.outdir}')
        os.makedirs(cfg.outdir, 0o755)

    if not os.path.exists(cfg.resize_dir):
        _logger.debug(f'Creating resize directory: {cfg.resize_dir}')
        os.makedirs(cfg.resize_dir, 0o755)

    with open(cfg.log_file or os.devnull, 'at', encoding = 'utf-8') as log:
        log.write(f'# {ISO_8601_time_stamp()}\n')
        for name, url in image_locations(args.images):
            _logger.info(f'[*] {name} <-- {url}')
            try:
                get_image_and_resize(url, cfg.width, cfg.height,
                    os.path.join(cfg.outdir, name), cfg.resize_dir)
                log.write(f'{name} = {url}\n')
            except:
                _logger.exception('Exception occurred.')

if '__main__' == __name__: main()
