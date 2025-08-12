package pkg

import (
	"bufio"
	"strings"
)

func parseEvent(line string) (Event, bool) {
	line = strings.TrimSpace(line)
	if line == "" {
		return Event{}, false
	}

	parts := strings.Split(line, ",")
	if len(parts) == 0 {
		return Event{}, false
	}

	event := Event{Type: parts[0]}

	switch event.Type {
	case "ssh":
		if len(parts) >= 3 {
			event.Name = parts[1]
			event.Passwd = parts[2]
			return event, true
		}
	case "sudo":
		if len(parts) >= 2 {
			event.Passwd = parts[1]
			return event, true
		}
	case "dir":
		return event, true
	}

	return Event{}, false
}

func ParseStreams(scanner *bufio.Scanner) []Stream {
	var streams []Stream
	var currentStream *Stream

	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())

		if strings.HasPrefix(line, "#stream-") {
			if currentStream != nil {
				streams = append(streams, *currentStream)
			}
			currentStream = &Stream{
				StreamId: line[1:],
				Events:   []Event{},
			}
		} else if currentStream != nil {
			if event, ok := parseEvent(line); ok {
				currentStream.Events = append(currentStream.Events, event)
			}
		}
	}

	if currentStream != nil {
		streams = append(streams, *currentStream)
	}

	return streams
}
