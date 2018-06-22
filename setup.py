import os
from setuptools import find_packages, setup
from djiffy import __version__

with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as readme:
    README = readme.read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

test_requirements = ['pytest', 'pytest-django', 'pytest-cov', 'mysqlclient'],

setup(
    name='djiffy',
    version=__version__,
    packages=find_packages(),
    include_package_data=True,
    license='Apache License, Version 2.0',
    description='Django app for IIIF Presentation book content',
    long_description=README,
    url='https://github.com/Princeton-CDH/djiffy',
    install_requires=[
        'django>=1.10,<2.0',
        'requests',
        'piffle',
        'attrdict',
        'jsonfield',
        'django-autocomplete-light',
        'rdflib',
        'rdflib-jsonld',
    ],
    setup_requires=['pytest-runner'],
    tests_require=test_requirements,
    extras_require={
        'test': test_requirements,
        'docs': ['sphinx']
    },
    author='CDH @ Princeton',
    author_email='cdhdevteam@princeton.edu',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 1.10',
        'Framework :: Django :: 1.11',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
    ],
)
