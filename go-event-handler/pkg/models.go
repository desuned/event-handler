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

var Users = [10]User{
	{
		Name:        "superadmin",
		Passwd:      "P@ssw0rd!",
		Sudo:        true,
		AuthRetries: 0,
		SudoRetries: 0,
		Mu:          sync.Mutex{},
	},
	{
		Name:        "auditor",
		Passwd:      "Secur3!2023",
		Sudo:        true,
		AuthRetries: 0,
		SudoRetries: 0,
		Mu:          sync.Mutex{},
	},
	{
		Name:        "dev_user",
		Passwd:      "d3v3l0p3r",
		Sudo:        true,
		AuthRetries: 0,
		SudoRetries: 0,
		Mu:          sync.Mutex{},
	},
	{
		Name:        "tester",
		Passwd:      "t3st3r!123",
		Sudo:        false,
		AuthRetries: 0,
		SudoRetries: 0,
		Mu:          sync.Mutex{},
	},
	{
		Name:        "analyst",
		Passwd:      "Data2023!",
		Sudo:        false,
		AuthRetries: 0,
		SudoRetries: 0,
		Mu:          sync.Mutex{},
	},
	{
		Name:        "support",
		Passwd:      "HelpDesk!",
		Sudo:        false,
		AuthRetries: 0,
		SudoRetries: 0,
		Mu:          sync.Mutex{},
	},
	{
		Name:        "reports",
		Passwd:      "R3port$",
		Sudo:        false,
		AuthRetries: 0,
		SudoRetries: 0,
		Mu:          sync.Mutex{},
	},
	{
		Name:        "backup",
		Passwd:      "B@ckUp123",
		Sudo:        true,
		AuthRetries: 0,
		SudoRetries: 0,
		Mu:          sync.Mutex{},
	},
	{
		Name:        "api_user",
		Passwd:      "Ap1K3y!2023",
		Sudo:        true,
		AuthRetries: 0,
		SudoRetries: 0,
		Mu:          sync.Mutex{},
	},
	{
		Name:        "guest",
		Passwd:      "T3mpPass!",
		Sudo:        false,
		AuthRetries: 0,
		SudoRetries: 0,
		Mu:          sync.Mutex{},
	},
}
