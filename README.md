# Coffee Machine

## Setup

Create Python virtual environment
`python -m venv .venv`

Activate venv
- Windows : `.venv\Scripts\activate.bat`
- Linux : `source venv/bin/activate`

Install requirements
`python -m pip install -r requirements.txt`

## Run
```
python app.py -h
usage: app.py [-h] [--host HOST] [--port PORT] [--timeout TIMEOUT]

options:
  -h, --help         show this help message and exit
  --host HOST        IP Address (ipv4/6)
  --port PORT        port to use
  --timeout TIMEOUT  socket timeout in seconds
```

## Flask
1. Open `localhost:5000` (Flask default)

## Tests

1.Launch coffee machine
2. Run tests on the left -- See results on the right 
![image](https://user-images.githubusercontent.com/28791624/174411292-4c06550c-ce56-4fa4-a5a3-83ea96cb5c84.png)
