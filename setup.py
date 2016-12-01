#!/usr/bin/python3

from setuptools import setup

setup(name='jenkey',
      version='0.1',
      description='Simple Jenkins job DSL helpers',
      url='http://github.com/redrampage/jenkey',
      author='RedRampage',
      author_email='redrampage@gmail.com',
      license='GPLv3',
      packages=['jenkey'],
      package_data={'templates': ['templates/*']},
      install_requires=[
        'jinja2',
        'python-jenkins',
      ],
      zip_safe=False)
