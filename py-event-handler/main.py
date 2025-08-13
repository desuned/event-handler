import logging
from typing import List, Dict
from dataclasses import dataclass, field
import asyncio

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
    mu: asyncio.Lock = field(default_factory=asyncio.Lock)  # Заменили на asyncio.Lock

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

    async def handle_ssh(self, stream_id: str, event: Event) -> None:
        prevCuid = self.cuid
        for uid, user in USERS.items():
            if event.name == user.name:
                self.cuid = uid
                break

        if self.cuid == -1:
            logger.error(f"Couldn't find a user with a name {event.name} ({stream_id})")
            return

        user = USERS[self.cuid]
        async with user.mu:  # Используем async with для asyncio.Lock

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

    async def handle_sudo(self, stream_id: str, event: Event) -> None:
        if self.cuid == -1:
            return

        user = USERS[self.cuid]
        if event.passwd == user.passwd:
            logger.info(f"Accepted sudo on user {user.name} ({stream_id})")
        else:
            logger.error(f"Bad password for sudo on user {user.name} ({stream_id})")

    async def handle_dir(self, stream_id: str, event: Event) -> None:
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

async def read_and_parse_file(file_path: str) -> List[Stream]:
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

async def handle_stream(stream: Stream) -> None:
    try:
        cu = CurrentUser()
        stream_id = stream.stream_id

        for event in stream.events:
            if event.type == "ssh":
                await cu.handle_ssh(stream_id, event)
            elif event.type == "sudo":
                await cu.handle_sudo(stream_id, event)
            elif event.type == "dir":
                await cu.handle_dir(stream_id, event)
    except Exception as e:
        logger.error(f"Ошибка в потоке {stream.stream_id}: {e}")

async def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage: python script.py <file_path>")
        return

    file_path = sys.argv[1]
    streams = await read_and_parse_file(file_path)

    if not streams:
        return

    start_time = asyncio.get_event_loop().time()  # Замер времени в asyncio

    tasks = []
    for stream in streams:
        task = asyncio.create_task(handle_stream(stream))
        tasks.append(task)

    await asyncio.gather(*tasks)  # Ожидаем завершения всех корутин

    end_time = asyncio.get_event_loop().time()
    elapsed = (end_time - start_time) * 1e9  # Переводим в наносекунды
    print(f"Обработка всех потоков заняла {elapsed:.2f} наносекунд")

if __name__ == "__main__":
    asyncio.run(main())  # Запуск асинхронного кода
