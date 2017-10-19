from os import path
from setuptools import setup, find_packages
from codecs import open


here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()


install_requires = []
with open(path.join(here, 'requirements.txt'), encoding='utf-8') as requirements:
    for line in requirements:
        line = line.strip()
        if line and not line.startswith('#'):
            install_requires.append(line)

setup(
    name = 'multiprocessing_utils',
    version = '0.2',
    url='https://github.com/daggaz/python-multiprocessing-utils',
    description='Multiprocessing utils (shared locks and thread locals)',
    long_description=long_description,
    author='Jamie Cockburn and Andrew Binnie',
    author_email='jamie_cockburn@hotmail.co.uk',
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: MIT License',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    packages=find_packages(exclude=['tests']),
    install_requires=install_requires,
    extras_require={
        'test': ['tox'],
    },
)
