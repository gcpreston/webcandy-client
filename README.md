# Webcandy Client
Client-side code for communicating with the Webcandy server and controlling lighting configuration. This should be run by the machine with LEDs connected to it via Fadecandy.

## Running
To run the client in order to receive lighting change requests from the server, use the `wc-client` executable:

`$ wc-client <username> <password> <client_id>`.

To manually change the lighting configuration offline, use the `wc-controller` executable:

`$ wc-controller --file <config JSON path>`

For usage information on either script, pass `--help`.