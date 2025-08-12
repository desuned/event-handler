import logging
from typing import List, Dict
from dataclasses import dataclass, field
import threading
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger()

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
    mu: threading.Lock = field(default_factory=threading.Lock)

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

class CurrentUser:
    def __init__(self):
        self.cuid = -1

    def handle_ssh(self, stream_id: str, event: Event) -> None:
        prevCuid = self.cuid
        for uid, user in USERS.items():
            if event.name == user.name:
                self.cuid = uid
                break

        if self.cuid == -1:
            logger.error(f"Couldn't find a user with a name {event.name} ({stream_id})")
            return

        user = USERS[self.cuid]
        with user.mu:

            if user.authd == stream_id:
                logger.info(f"You are already logged in ({stream_id})")
                return

            if user.authd:
                logger.error(f"User {user.name} already authd from {user.authd} ({stream_id})")
                self.cuid = -1
                return

            if user.auth_retries >= 3:
                logger.error(f"Can't access user {user.name}, user is blocked ({stream_id})")
                self.cuid = -1
                return

            if event.passwd != user.passwd:
                user.auth_retries += 1
                logger.error(f"Wrong password for user {user.name} ({stream_id})")
                self.cuid = -1
                return

            if not user.authd:
                if (prevCuid != -1):
                    USERS[prevCuid].authd = ""
                user.authd = stream_id
                user.auth_retries = 0
                logger.info(f"User {user.name} authd ({stream_id})")
                return

    def handle_sudo(self, stream_id: str, event: Event) -> None:
        if self.cuid == -1:
            return

        user = USERS[self.cuid]
        if event.passwd == user.passwd:
            logger.info(f"Accepted sudo on user {user.name} ({stream_id})")
        else:
            logger.error(f"Bad password for sudo on user {user.name} ({stream_id})")

    def handle_dir(self, stream_id: str, event: Event) -> None:
        if self.cuid == -1:
            return
        logger.info(f"Accepted dir on user {USERS[self.cuid].name} ({stream_id})")

def parse_streams(data: str) -> List[Stream]:
    streams = []
    stream_blocks = data.strip().split('#')[1:]

    for block in stream_blocks:
        if not block.strip():
            continue

        lines = block.strip().split('\n')
        stream_id = lines[0]
        event_lines = lines[1:]

        events = []
        for line in event_lines:
            if not line.strip():
                continue

            parts = line.split(',')
            if parts[0] == 'ssh':
                if len(parts) >= 3:
                    events.append(Event(type_='ssh', name=parts[1], passwd=parts[2]))
            elif parts[0] == 'sudo':
                if len(parts) >= 2:
                    events.append(Event(type_='sudo', name=parts[1]))
            elif parts[0] == 'dir':
                events.append(Event(type_='dir'))

        streams.append(Stream(stream_id=stream_id, events=events))

    return streams

def read_and_parse_file(file_path: str) -> List[Stream]:
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = file.read()
            return parse_streams(data)
    except FileNotFoundError:
        logger.error(f"Ошибка: файл {file_path} не найден")
        return []
    except Exception as e:
        logger.error(f"Ошибка при чтении файла: {e}")
        return []

def handle_stream(stream: Stream, wg: threading.Event) -> None:
    try:
        cu = CurrentUser()
        stream_id = stream.stream_id

        for event in stream.events:
            if event.type == "ssh":
                cu.handle_ssh(stream_id, event)
            elif event.type == "sudo":
                cu.handle_sudo(stream_id, event)
            elif event.type == "dir":
                cu.handle_dir(stream_id, event)
    finally:
        if wg:
            wg.set()

def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage: python script.py <file_path>")
        return

    file_path = sys.argv[1]
    streams = read_and_parse_file(file_path)

    if not streams:
        return

    wait_events = []
    start_time = time.time_ns()  # Начало замера в наносекундах

    for stream in streams:
        event = threading.Event()
        wait_events.append(event)
        threading.Thread(target=handle_stream, args=(stream, event)).start()

    for event in wait_events:
        event.wait()

    end_time = time.time_ns()  # Конец замера
    elapsed = end_time - start_time
    print(f"Обработка всех потоков заняла {elapsed} наносекунд")

if __name__ == "__main__":
    main()
