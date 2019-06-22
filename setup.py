from setuptools import setup

setup(
    name='webcandy-client',
    packages=['webcandy_client'],
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
