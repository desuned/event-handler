package models

type Stream struct {
	StreamId string
	Events   []Event
}

type Event struct {
	Type   string
	Name   string
	Passwd string
}
