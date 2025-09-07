from typing import List, Dict
from dataclasses import dataclass, field
from multiprocessing import Manager, Process, Pool
from concurrent.futures import ProcessPoolExecutor
from pkg.models import Event, Stream, User, USERS
from pkg.parse import logger, read_and_parse_file
import sys
import time

class ParallelUserHandler:
    def __init__(self, users_dict, locks_dict):
        self.users = users_dict
        self.locks = locks_dict

    def handle_ssh(self, stream_id: str, event: Event) -> bool:
        user = next((u for u in self.users.values() if u['name'] == event.name), None)
        if not user:
            logger.error(f"User {event.name} not found ({stream_id})")
            return False

        with self.locks[user['id']]:
            if user['authd'] == stream_id:
                logger.info(f"Already logged in ({stream_id})")
                return True

            if user['authd']:
                logger.error(f"User {user['name']} already authed from {user['authd']} ({stream_id})")
                return False

            if user['retries'] >= 3:
                logger.error(f"User {user['name']} blocked ({stream_id})")
                return False

            if event.passwd != user['passwd']:
                user['retries'] += 1
                logger.error(f"Wrong password for {user['name']} ({stream_id})")
                return False

            user['authd'] = stream_id
            user['retries'] = 0
            logger.info(f"User {user['name']} authed ({stream_id})")
            return True

    def handle_sudo(self, stream_id: str, event: Event) -> None:
        user = next((u for u in self.users.values() if u['name'] == event.name), None)
        if not user:
            return

        if event.passwd == user['passwd']:
            logger.info(f"Sudo granted for {user['name']} ({stream_id})")
        else:
            logger.error(f"Bad sudo password for {user['name']} ({stream_id})")

    def handle_dir(self, stream_id: str, event: Event) -> None:
        logger.info(f"Directory access granted ({stream_id})")

def process_stream(stream: Stream, users_dict, locks_dict):
    handler = ParallelUserHandler(users_dict, locks_dict)
    for event in stream.events:
        if event.type == "ssh":
            handler.handle_ssh(stream.stream_id, event)
        elif event.type == "sudo":
            handler.handle_sudo(stream.stream_id, event)
        elif event.type == "dir":
            handler.handle_dir(stream.stream_id, event)

class UsersManager:
    def __init__(self):
        self.manager = Manager()
        self.users = self.manager.dict()
        self.locks = self.manager.dict()

        for uid, user in USERS.items():
            self.users[uid] = self.manager.dict({
                'id': uid,
                'name': user.name,
                'passwd': str(user.passwd),
                'authd': '',
                'retries': 0
            })
            self.locks[uid] = self.manager.Lock()

    def get_shared_data(self):
        """Возвращает данные, которые можно безопасно передавать между процессами"""
        return self.users, self.locks

def main():
    if len(sys.argv) < 2:
        print("Usage: python script.py <file_path>")
        return

    file_path = sys.argv[1]
    streams = read_and_parse_file(file_path)

    if not streams:
        return

    users_manager = UsersManager()
    users_dict, locks_dict = users_manager.get_shared_data()

    num_processes = min(len(streams), 8)

    start_ns = time.perf_counter_ns()

    with Pool(processes=num_processes) as pool:
        pool.starmap(process_stream, [(s, users_dict, locks_dict) for s in streams])

    end_ns = time.perf_counter_ns()
    elapsed_ns = end_ns - start_ns

    print(f"Обработка всех потоков заняла {elapsed_ns} наносекунд")

if __name__ == "__main__":
    main()
