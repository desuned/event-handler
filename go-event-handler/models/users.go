package models

import "sync"

type User struct {
	Name        string
	Passwd      string
	Sudo        bool
	AuthStream  string
	AuthRetries int
	SudoRetries int
	Mu          sync.Mutex
}

var Users = [10]User{
	{Name: "superadmin", Passwd: "P@ssw0rd!", Sudo: true},
	{Name: "auditor", Passwd: "Secur3!2023", Sudo: true},
	{Name: "dev_user", Passwd: "d3v3l0p3r", Sudo: true},
	{Name: "tester", Passwd: "t3st3r!123", Sudo: false},
	{Name: "analyst", Passwd: "Data2023!", Sudo: false},
	{Name: "support", Passwd: "HelpDesk!", Sudo: false},
	{Name: "reports", Passwd: "R3port$", Sudo: false},
	{Name: "backup", Passwd: "B@ckUp123", Sudo: true},
	{Name: "api_user", Passwd: "Ap1K3y!2023", Sudo: true},
	{Name: "guest", Passwd: "T3mpPass!", Sudo: false},
}
