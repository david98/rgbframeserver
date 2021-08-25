import subprocess
from conf import users, firmware_version

from fastapi import FastAPI
import uvicorn
from fastapi.responses import FileResponse, PlainTextResponse


class User:
    def __init__(self, username: str, hashed_password: str):
        self.username = username
        self.hashed_password = hashed_password
        self.devices = []

    def __str__(self):
        return self.username + ":" + self.hashed_password


class Device:
    def __init__(self, name: str, room: str, clientID: str, owner: User):
        self.name = name
        self.room = room
        self.clientID = clientID
        self.owner = owner

    def __str__(self):
        return '{{"name": "{0}", "room": "{1}", "clientID": "{3}", "owner": {{"username": "{2}" }}}}'.format(
            self.name, self.room, self.owner.username, self.clientID
        )


app = FastAPI()


@app.get("/")
async def read_root():
    return {"Hello": "World"}


@app.get("/version", response_class=PlainTextResponse)
async def read_version():
    return firmware_version


@app.get("/update")
async def read_update():
    return FileResponse("data/firmware.bin", filename="firmware.bin")


if __name__ == "__main__":
    parsed_users = [User(u["username"], u["password"]) for u in users]
    print("Loaded users: {0}".format([str(u) for u in parsed_users]))
    devices = []

    for u in users:
        device_strings = u["devices"]
        for s in device_strings:
            owner = next(
                filter(lambda user: user.username == u["username"], parsed_users)
            )
            device = Device(
                s["name"],
                s["room"],
                s["clientID"],
                owner,
            )
            devices.append(device)
            owner.devices.append(device)
    print("Loaded devices: {0}".format([str(d) for d in devices]))

    with open("passwd.txt", "w", encoding="utf-8") as f:
        for user in parsed_users:
            f.write(str(user))
            f.write("\n")

    with open("acl.txt", "w", encoding="utf-8") as f:
        for user in parsed_users:
            f.write("user {0}\n".format(user.username))
            for device in user.devices:
                f.write(
                    "topic {0}/{1}/{2}/strip\n".format(
                        user.username, device.room, device.name
                    )
                )
                f.write(
                    "topic {0}/{1}/{2}/controller\n".format(
                        user.username, device.room, device.name
                    )
                )
            f.write("\n")

    mosquitto_process = subprocess.Popen(
        ["/opt/homebrew/opt/mosquitto/sbin/mosquitto", "-c", "mosquitto.conf"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    uvicorn.run("main:app", host="0.0.0.0", port=8000, log_level="info")
