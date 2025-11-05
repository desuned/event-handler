package models

type Stream struct {
	StreamId string  `json:"streamId"`
	Events   []Event `json:"events"`
}

type Event struct {
	Type   string `json:"type"`
	Name   string `json:"name"`
	Passwd string `json:"passwd"`
}
