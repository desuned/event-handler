import logging
import threading
from multiprocessing import Process, Lock, Event, Value, Manager
import time
from typing import List, Dict
from dataclasses import dataclass, field
from flask import Flask, request, jsonify

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger()

class EventObj:
    def __init__(self, type_: str, name: str = "", passwd: str = ""):
        self.type = type_
        self.name = name
        self.passwd = passwd

class Stream:
    def __init__(self, stream_id: str, events: List[EventObj]):
        self.stream_id = stream_id
        self.events = events if events else []

@dataclass
class User:
    name: str
    passwd: str
    authd: str = ""
    auth_retries: int = 0

manager = Manager()
USERS: Dict[int, User] = manager.dict({
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
})

def handle_stream(stream: Stream, total_time: Value, lock: Lock):
    cu_cuid = -1
    start_ns = time.perf_counter_ns()

    for event in stream.events:
        if event.type == "ssh":
            for uid, user in USERS.items():
                if event.name == user.name:
                    cu_cuid = uid
                    break
            if cu_cuid != -1:
                user = USERS[cu_cuid]
                if event.passwd == user.passwd:
                    user.authd = stream.stream_id
                    logger.info(f"User {user.name} authd ({stream.stream_id})")
                else:
                    logger.error(f"Wrong password for user {user.name} ({stream.stream_id})")
        elif event.type == "sudo":
            if cu_cuid != -1:
                user = USERS[cu_cuid]
                if event.passwd == user.passwd:
                    logger.info(f"Accepted sudo on user {user.name} ({stream.stream_id})")
                else:
                    logger.error(f"Bad password for sudo on user {user.name} ({stream.stream_id})")
        elif event.type == "dir":
            if cu_cuid != -1:
                user = USERS[cu_cuid]
                logger.info(f"Accepted dir on user {user.name} ({stream.stream_id})")

    elapsed_ns = time.perf_counter_ns() - start_ns
    with lock:
        total_time.value += elapsed_ns

    logger.info(f"Завершение потока {stream.stream_id} за {elapsed_ns/1e3:.3f} мс")

app = Flask(__name__)
MAX_STREAMS = 50
manager_lock = Lock()
total_time = Value('L', 0)
total_streams = Value('i', 0)
done_event = Event()
processes: List[Process] = []

@app.route("/", methods=["POST"])
def receive_stream():
    data = request.get_json()
    if not data or "streamId" not in data or "events" not in data:
        return jsonify({"error": "Invalid JSON"}), 400

    stream_id = data["streamId"]
    events = [EventObj(ev.get("type", ""), ev.get("name", ""), ev.get("passwd", "")) for ev in data["events"]]
    stream = Stream(stream_id, events)

    with manager_lock:
        if total_streams.value >= MAX_STREAMS:
            return jsonify({"error": "Maximum streams limit reached"}), 429
        total_streams.value += 1
        current_count = total_streams.value

    p = Process(target=handle_stream, args=(stream, total_time, manager_lock))
    p.start()
    processes.append(p)

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

    if not done_event.wait(timeout=30*60):
        logger.info("Таймаут, завершаем работу...")
    else:
        logger.info("Достигнут лимит потоков, завершаем работу...")

    server.shutdown()
    thread.join()

    for p in processes:
        p.join()

    logger.info(
        f"Полное чистое время обработки: {total_time.value/1e3:.3f} мс, "
        f"среднее на поток: {(total_time.value/total_streams.value)/1e3:.3f} мс"
    )

if __name__ == "__main__":
    main()
