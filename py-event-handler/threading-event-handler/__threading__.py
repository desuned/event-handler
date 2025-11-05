import logging
import threading
import time
from typing import List, Dict
from dataclasses import dataclass, field
from flask import Flask, request, jsonify

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger()

# --------- модели ---------
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

# --------- обработка ---------
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
                if prevCuid != -1:
                    USERS[prevCuid].authd = ""
                user.authd = stream_id
                user.auth_retries = 0
                logger.info(f"User {user.name} authd ({stream_id})")

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

def handle_stream(stream: Stream):
    global total_time
    cu = CurrentUser()
    stream_id = stream.stream_id
    start_ns = time.perf_counter_ns()  # старт в наносекундах

    for event in stream.events:
        if event.type == "ssh":
            cu.handle_ssh(stream_id, event)
        elif event.type == "sudo":
            cu.handle_sudo(stream_id, event)
        elif event.type == "dir":
            cu.handle_dir(stream_id, event)

    elapsed_ns = time.perf_counter_ns() - start_ns

    with streams_lock:
        total_time += elapsed_ns

    # выводим в миллисекундах с 3 знаками после запятой
    logger.info(f"Завершение потока {stream_id} за {elapsed_ns/1e3:.3f} мкс")

# --------- сервер ---------
app = Flask(__name__)
MAX_STREAMS = 50
total_streams = 0
total_time = 0.0
streams_lock = threading.Lock()
done_event = threading.Event()
threads = []

@app.route("/", methods=["POST"])
def receive_stream():
    global total_streams, total_time

    data = request.get_json()
    if not data or "streamId" not in data or "events" not in data:
        return jsonify({"error": "Invalid JSON"}), 400

    stream_id = data["streamId"]
    events = [Event(ev.get("type", ""), ev.get("name", ""), ev.get("passwd", "")) for ev in data["events"]]
    stream = Stream(stream_id, events)

    with streams_lock:
        if total_streams >= MAX_STREAMS:
            return jsonify({"error": "Maximum streams limit reached"}), 429

        total_streams += 1
        current_count = total_streams

    t = threading.Thread(target=handle_stream, args=(stream,))
    t.start()
    threads.append(t)

    if current_count == MAX_STREAMS:
        done_event.set()

    return jsonify({
        "status": "processing_started",
        "stream_id": stream.stream_id,
        "count": f"{current_count}/{MAX_STREAMS}",
    })

def main():
    from werkzeug.serving import make_server

    server = make_server("0.0.0.0", 8081, app)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    logger.info("Server starting on :8081")

    # ждём или лимита, или таймаута
    if not done_event.wait(timeout=30*60):
        logger.info("Таймаут, завершаем работу...")
    else:
        logger.info("Достигнут лимит потоков, завершаем работу...")

    server.shutdown()
    for t in threads:
        t.join()

    logger.info(
        f"Полное чистое время обработки: {total_time/1e3:.3f} мкс, "
        f"среднее на поток: {(total_time/total_streams)/1e3:.3f} мкс"
    )
    logger.info("Все потоки завершены")

if __name__ == "__main__":
    main()
