#!/usr/bin/env python

"""The setup script."""

from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [
    'Click>=7.0',
    'aleph-sdk-python>=0.8.0',
    'plyvel>=1.5.0',
    'python-dotenv',
    'setuptools',
    'web3'
]

test_requirements = [ ]

setup(
    author="David Amelekh",
    author_email='david.amelekh@protonmail.com',
    python_requires='>=3.6',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    description="Libertai Points Calculator",
    entry_points={
        'console_scripts': [
            'ltai_points=ltai_points.cli:main',
        ],
    },
    install_requires=requirements,
    license="MIT license",
    long_description=readme + '\n\n' + history,
    include_package_data=True,
    keywords='ltai_points',
    name='ltai_points',
    packages=find_packages(include=['ltai_points', 'ltai_points.*']),
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/davidamelekh/ltai_points',
    version='0.1.0',
    zip_safe=False,
)
