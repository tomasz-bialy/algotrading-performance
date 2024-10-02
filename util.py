import websocket, json
from datetime import datetime
import requests
import pandas as pd
from datetime import date

class Broker:
    def __init__(self, ID, PSW):
        self.ID = ID
        self.PSW = PSW
        self.ws = websocket.create_connection("wss://ws.xtb.com/real")
        self.login()

    def login(self):
        login = {
            "command": "login",
            "arguments": {
                "userId": self.ID,
                "password": self.PSW
            }
        }
        self.send(json.dumps(login))

    def logout(self):
        logout = {"command": "logout"}
        self.send(json.dumps(logout))
        self.ws.close()

    def get_History(self, start):
        history = {
            "command": "getTradesHistory",
            "arguments": {
                "start": self.time_conversion(start),
                "end": self.get_ServerTime()
            }
        }
        result = self.send(json.dumps(history))
        return json.loads(result)

    def get_ServerTime(self):
        time = {"command": "getServerTime"}
        result = self.send(json.dumps(time))
        return json.loads(result)["returnData"]["time"]

    def time_conversion(self, date_str):
        start_epoch = datetime(1970, 1, 1)
        date = datetime.strptime(date_str, '%m/%d/%Y %H:%M:%S')
        return int((date - start_epoch).total_seconds() * 1000)

    def send(self, msg):
        self.ws.send(msg)
        return self.ws.recv()
    
class DataLoader:
    def __init__(self, from_date: date, to_date: date):
        self.from_date = from_date
        self.to_date = to_date

    def fetch_index(self) -> pd.DataFrame:
        url = (
            'https://gpwbenchmark.pl/chart-json.php'
            f'?req=[{{'
            f'"isin": "PL9999999375", '
            f'"mode": "RANGE", '
            f'"from": "{self.from_date:%Y-%m-%d}", '
            f'"to": "{self.to_date:%Y-%m-%d}"'
            f'}}]'
        )
        response = requests.get(url)
        data = response.json()[0]["data"]
        df = pd.DataFrame({
            "date": [date.fromtimestamp(item["t"]) for item in data],
            "index_close": [item["c"] for item in data]
        })
        df.set_index("date", inplace=True)
        df = df.asfreq('B', method="ffill")
        df = df.reset_index()
        df['date'] = df['date'].dt.date
        return df