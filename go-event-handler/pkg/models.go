package pkg

import "sync"

type User struct {
	Name        string
	Passwd      string
	Sudo        bool
	Authd       string
	AuthRetries int
	SudoRetries int
	Mu          sync.Mutex
	Blocked     bool
}

type Stream struct {
	StreamId string
	Events   []Event
}

type Event struct {
	Type   string
	Name   string
	Passwd string
}

var Users = [3]User{
	{
		Name:        "admin",
		Passwd:      "admin",
		Sudo:        true,
		AuthRetries: 0,
		SudoRetries: 0,
		Mu:          sync.Mutex{},
	},
	{
		Name:        "admin123",
		Passwd:      "admin",
		Sudo:        true,
		AuthRetries: 0,
		SudoRetries: 0,
		Mu:          sync.Mutex{},
	},
	{
		Name:        "user",
		Passwd:      "user",
		Sudo:        false,
		AuthRetries: 0,
		SudoRetries: 0,
		Mu:          sync.Mutex{},
	},
}
