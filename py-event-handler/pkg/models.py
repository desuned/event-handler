from dataclasses import dataclass, field
from typing import List, Dict
import asyncio

class Event:
    def __init__(self, type_: str, name: str = "", passwd: str = ""):
        self.type = type_
        self.name = name
        self.passwd = passwd

    def __repr__(self):
        return f"Event(type='{self.type}', name='{self.name}', passwd='{self.passwd}')"

class Stream:
    def __init__(self, stream_id: str, events: List[Event]):
        self.stream_id = stream_id
        self.events = events if events is not None else []

    def __repr__(self):
        return f"Stream(stream_id='{self.stream_id}', events={self.events})"

@dataclass
class User:
    name: str
    passwd: str
    authd: str = ""
    auth_retries: int = 0
    mu: asyncio.Lock = field(default_factory=asyncio.Lock)

USERS: Dict[int, User] = {
    0: User(name="superadmin", passwd="P@ssw0rd!"),
    1: User(name="auditor", passwd="Secur3!2023"),
    2: User(name="dev_user", passwd="d3v3l0p3r"),
    3: User(name="tester", passwd="t3st3r!123"),
    4: User(name="analyst", passwd="Data2023!"),
    5: User(name="support", passwd="HelpDesk!"),
    6: User(name="reports", passwd="R3port$"),
    7: User(name="backup", passwd="B@ckUp123"),
    8: User(name="api_user", passwd="Ap1K3y!2023"),
    9: User(name="guest", passwd="T3mpPass!")
}
