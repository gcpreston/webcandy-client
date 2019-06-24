from setuptools import setup, find_packages

with open('README.md') as readme:
    long_description = readme.read()

setup(
    name='webcandy-client',
    version='0.0.1',
    author='Graham Preston',
    author_email='graham.preston@gmail.com',
    description='Client-side code for communicating with a Webcandy server.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/gcpreston/webcandy-client',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'requests',
        'websockets'
    ],
    entry_points={
        'console_scripts': [
            'wc-client = webcandy_client.client:main',
            'wc-controller = webcandy_client.controller:main'
        ]
    }
)
