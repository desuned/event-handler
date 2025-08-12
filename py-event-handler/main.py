from typing import List

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
        print(f"Ошибка: файл {file_path} не найден")
        return []
    except Exception as e:
        print(f"Ошибка при чтении файла: {e}")
        return []

if __name__ == "__main__":
    file_path = "../data/streams.txt"

    streams = read_and_parse_file(file_path)
    for stream in streams:
        print(stream)
