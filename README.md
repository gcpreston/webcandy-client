# Webcandy Client
Client-side code for communicating with the Webcandy server and controlling
lighting configuration. This should be run by the machine with LEDs connected to
it via Fadecandy.

## Installation
The easiest way to install is to run `pip install webcandy-client`. If you want
the absolute latest code, you can clone this repository and run
`pip install -e .` from the root directory.

### Development
This project uses [Pipenv](https://docs.pipenv.org/en/latest/) for dependancy
management. If you want to set up a development environment, make sure you have
Pipenv installed and run `pipenv install` from the root directory.

## Running
To run the client in order to receive lighting change requests from the server,
use the `wc-client` executable:

`$ wc-client <username> <password> <client_id>`.

To manually change the lighting configuration offline, use the `wc-controller`
executable:

`$ wc-controller --file <config JSON path>`

For usage information on either script, pass `--help`.