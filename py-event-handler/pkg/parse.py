import logging
from typing import List
from dataclasses import dataclass, field
import asyncio
from pkg.models import Event, Stream, USERS

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger()

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
