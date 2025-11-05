import logging
from typing import List, Dict
from dataclasses import dataclass, field
import asyncio
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
import uvicorn
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
        async with user.mu:

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

MAX_STREAMS = 50
TIMEOUT = 30 * 60
total_streams = 0
total_time_ns = 0
done_event = asyncio.Event()
semaphore = asyncio.Semaphore(MAX_STREAMS)
lock = asyncio.Lock()
running_tasks = set()


app = FastAPI()

class StreamIn(BaseModel):
    stream_id: str
    events: list[dict]

async def worker(stream: Stream):
    global total_time_ns
    async with semaphore:
        start_ns = time.perf_counter_ns()
        await handle_stream(stream)
        dur_ns = time.perf_counter_ns() - start_ns

    async with lock:
        total_time_ns += dur_ns

    logger.info(f"Завершение потока {stream.stream_id} за {dur_ns/1000:.3f} мкс")


@app.post("/")
async def receive_stream(req: Request):
    global total_streams
    payload = await req.json()
    stream = Stream(
        stream_id=payload["streamId"],
        events=[Event(type_=ev.get("type",""), name=ev.get("name",""), passwd=ev.get("passwd",""))
                for ev in payload.get("events", [])]
    )

    async with lock:
        if total_streams >= MAX_STREAMS:
            raise HTTPException(status_code=429, detail="Maximum streams limit reached")
        total_streams += 1
        current_count = total_streams

    t = asyncio.create_task(worker(stream))
    running_tasks.add(t)
    t.add_done_callback(running_tasks.discard)

    if current_count == MAX_STREAMS:
        asyncio.create_task(trigger_done())

    return {
        "status": "processing_started",
        "stream_id": stream.stream_id,
        "count": f"{current_count}/{MAX_STREAMS}"
    }


async def trigger_done():
    await asyncio.sleep(0.1)
    done_event.set()

async def start_server():
    config = uvicorn.Config(app, host="0.0.0.0", port=8081, log_level="info", loop="asyncio")
    server = uvicorn.Server(config)
    await server.serve()

import contextlib

async def main():
    config = uvicorn.Config(app, host="0.0.0.0", port=8081, log_level="info", loop="asyncio")
    server = uvicorn.Server(config)

    server_task = asyncio.create_task(server.serve())

    try:
        await asyncio.wait_for(done_event.wait(), timeout=TIMEOUT)
    finally:
        server.should_exit = True

    await server_task

    if running_tasks:
        await asyncio.gather(*list(running_tasks), return_exceptions=True)

    avg_ns = total_time_ns / total_streams if total_streams else 0
    logger.info(
        "Полное чистое время обработки: %.3f мкс, среднее на поток: %.3f мкс"
        % (total_time_ns/1e3, avg_ns/1e3)
    )



if __name__ == "__main__":
    asyncio.run(main())
