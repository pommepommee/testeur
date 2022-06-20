# Coffee Machine

## Rapports

détails de tests en pseudo code : `details_tests.pdf`
TPs = tps.pdf

## Setup

Create Python virtual environment
`python -m venv .venv`

Activate venv
- Windows : `.venv\Scripts\activate.bat`
- Linux : `source venv/bin/activate`

Install requirements
`python -m pip install -r requirements.txt`

Run app.py
```
python app.py -h
usage: app.py [-h] [--host HOST] [--port PORT] [--timeout TIMEOUT]

options:
  -h, --help         show this help message and exit
  --host HOST        IP Address (ipv4/6)
  --port PORT        port to use
  --timeout TIMEOUT  socket timeout in seconds
```

Open `localhost:5000` (Flask default)
