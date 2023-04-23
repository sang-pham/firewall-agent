# Firewall agent for DFW

### Intall steps:
- cp api.key.example api.key => add your key to this api.key file
- Run the following commands with root or sudo privilege to start the agent.
- Install related packages: pip3 install -r requirements.txt *or* pip install -r requirements.txt *or* pip install -r requirements2.txt(for low version).
- Run app with: *python3 app.py* with -h and -p options or default config in .env file to run the agent on specific host and port number.