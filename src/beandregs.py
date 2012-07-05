#!/usr/bin/python
#
# Copyright (c) 2012 Joshua Hughes <kivhift@gmail.com>
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
import contextlib
import logging
import os
import re
import shutil
import sys
import urllib2
import urlparse

import PIL.Image

import pu.utils

__version__ = '1.1.0'

_logger = logging.getLogger(__name__)
_defaults = dict(outdir = 'beandregs-output', resize_dir = 'beandregs-output',
    width = 300, height = 300, log_file = 'beandregs-images-log.ini')

def get_image_and_resize(url, width, height, basename, resize_dir = None):
    if os.path.exists(url):
        _logger.debug('Using local file.')
        url = 'file:///%s' % os.path.abspath(url)
    with contextlib.closing(urllib2.urlopen(url)) as u:
        path = urlparse.urlparse(u.geturl()).path
        ext = os.path.splitext(path)[1].lower()
        h, t = os.path.split(basename)
        orig = os.path.join(h, 'orig-' + t + ext)
        resized = basename + ext
        resize_not_needed = False
        if os.path.exists(orig):
            _logger.debug('%s already exists, clobbering.' % orig)
        with open(orig, 'w+b') as f:
            f.write(u.read())
            f.seek(0)
            im = PIL.Image.open(f)
            w, h = im.size
            if w <= width and h <= height:
                resize_not_needed = True
            else:
                _logger.debug('Resizing %s to %s.' % (orig, resized))
                im.thumbnail((width, height), PIL.Image.ANTIALIAS)
                im.save(resized)
        if resize_not_needed:
            if os.path.exists(resized):
                _logger.debug('%s already exists, removing.' % resized)
                os.remove(resized)
            _logger.debug('Resize not needed.  Renaming %s to %s.' % (
                orig, resized))
            os.rename(orig, resized)
        if resize_dir:
            absor = os.path.realpath(resized)
            absnr = os.path.realpath(os.path.join(
                resize_dir, os.path.basename(resized)))
            if absor != absnr:
                shutil.copy2(resized, resize_dir)
                _logger.debug('Copied %s to %s.' % (resized, resize_dir))

def load_config(cfg_file = None):
    _logger.debug('Load config file: %s' % cfg_file)
    if cfg_file:
        mod_name = 'beandregs-cfg'
        if pu.utils.is_a_string(cfg_file):
            with open(cfg_file, 'rb') as f:
                tmp = pu.utils.import_code(f, mod_name)
        else:
            tmp = pu.utils.import_code(cfg_file, mod_name)
    else:
        tmp = pu.utils.DataContainer()

    cfg = pu.utils.DataContainer(_defaults)
    for k in cfg:
        if hasattr(tmp, k):
            cfg[k] = getattr(tmp, k)

    return cfg

def image_locations(ims):
    with open(ims, 'rb') if pu.utils.is_a_string(ims) else ims as inf:
        for ln in inf:
            ln = re.sub(r'#.*$', '', ln)
            if '' == ln or ln.isspace(): continue
            yield [ x.strip() for x in ln.split('=', 1) ]

def _setup_logging(debug = False):
    L = logging.getLogger('')
    L.setLevel(logging.DEBUG)

    fh = logging.FileHandler(
        filename = os.path.join(os.curdir, 'beandregs.log'), mode = 'ab')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(' ][ '.join('''
        %(asctime)s
        %(levelname)s
        %(message)s
        %(module)s:%(lineno)d
        '''.split())))
    L.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG if debug else logging.INFO)
    ch.setFormatter(logging.Formatter('%(message)s'))
    L.addHandler(ch)

    L.debug('** Start beandregs v%s logging.' % __version__)
    atexit.register(L.debug, 'Stop.')

def main(args_list = None):
    arg_parser = argparse.ArgumentParser(
        description = 'Retrieve and (possibly) resize images.')
    _a = arg_parser.add_argument
    _a('-i', '--images', dest = 'images', default = sys.stdin,
        help = 'Image-location file to use. [default: stdin]')
    _a('-l', '--log', dest = 'log_file', default = None,
        help = 'Log successes to this file.')
    _a('-c', '--config', dest = 'config', help = 'Configuration file to use.')
    _a('-o', '--output-dir', dest = 'outdir',
        help = 'Directory to use for image output. [default: %s]' %
        _defaults['outdir'])
    _a('-r', '--resize-dir', dest = 'resize_dir',
        help = 'Directory to use for resized-image output. [default: %s' %
        _defaults['resize_dir'])
    _a('-W', '--width', dest = 'width', type = int,
        help = 'Width to resize to. [default: %d]' % _defaults['width'])
    _a('-H', '--height', dest = 'height', type = int,
        help = 'Height to resize to. [default: %d]' % _defaults['height'])
    _a('-d', '--debug', dest = 'debug', default = False, action = 'store_true',
        help = 'Send all logging output to console.')

    args = arg_parser.parse_args(args_list or sys.argv[1:])

    _setup_logging(args.debug)
    cfg = load_config(args.config)

    # Make command line take precedence over config file.
    cfg.height = args.height or cfg.height
    cfg.log_file = args.log_file or cfg.log_file
    cfg.outdir = os.path.expanduser(args.outdir or cfg.outdir)
    cfg.resize_dir = os.path.expanduser(args.resize_dir or cfg.resize_dir)
    cfg.width = args.width or cfg.width

    if not os.path.exists(cfg.outdir):
        _logger.debug('Creating output directory: %s' % cfg.outdir)
        os.makedirs(cfg.outdir, 0755)

    if not os.path.exists(cfg.resize_dir):
        _logger.debug('Creating resize directory: %s' % cfg.resize_dir)
        os.makedirs(cfg.resize_dir, 0755)

    log = open(cfg.log_file, 'ab') if cfg.log_file else None
    if log: log.write('# %s\n' % pu.utils.ISO_8601_time_stamp())
    for name, url in image_locations(args.images):
        _logger.info('[*] %s <-- %s' % (name, url))
        try:
            get_image_and_resize(url, cfg.width, cfg.height,
                os.path.join(cfg.outdir, name), cfg.resize_dir)
            if log: log.write('%s = %s\n' % (name, url))
        except:
            _logger.exception('Exception occurred.')
    if log: log.close()

if '__main__' == __name__: main()
