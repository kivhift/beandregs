import os
import sys
from setuptools import setup

root_dir = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(root_dir, 'src'))
import beandregs

readme = open(os.path.join(root_dir, 'README'), 'r').read()

setup(
    name = 'beandregs',
    author = 'Joshua Hughes',
    author_email = 'kivhift@gmail.com',
    version = beandregs.__version__,
    url = 'http://github.com/kivhift/beandregs',
    license = 'MIT',
    package_dir = { '' : 'src' },
    py_modules = ['beandregs'],
    description = 'An image retriever and resizer.',
    long_description = readme,
    classifiers = [
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python'
    ],
    entry_points = { 'console_scripts' : [ 'beandregs = beandregs:main' ] },
    zip_safe = False
)
