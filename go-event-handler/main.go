package main

import (
	"article/events-handler/pkg"
	"bufio"
	"fmt"
	"log"
	"os"
	"sync"
	"time"
)

type CurrentUser struct {
	Cuid int
}

func (cu *CurrentUser) HandleSSH(streamId string, event pkg.Event) {
	prevCuid := cu.Cuid
	for i := range pkg.Users {
		if event.Name == pkg.Users[i].Name {
			cu.Cuid = i
		}
	}

	if cu.Cuid == -1 {
		log.Printf("Couldn't find a user with a name %s (%s)",
			event.Name, streamId)
		return
	}

	pkg.Users[cu.Cuid].Mu.Lock()
	defer pkg.Users[cu.Cuid].Mu.Unlock()

	if pkg.Users[cu.Cuid].Authd == streamId {
		log.Printf("You are already logged in (%s)", streamId)
		return
	}

	if pkg.Users[cu.Cuid].Authd != "" {
		log.Printf("User %s already authd from %s (%s)",
			pkg.Users[cu.Cuid].Name, pkg.Users[cu.Cuid].Authd, streamId)
		cu.Cuid = -1
		return
	}

	if pkg.Users[cu.Cuid].AuthRetries >= 3 {
		log.Printf("Can't access user %s, user is blocked (%s)",
			pkg.Users[cu.Cuid].Name, streamId)
		cu.Cuid = -1
		return
	}

	if event.Passwd != pkg.Users[cu.Cuid].Passwd {
		pkg.Users[cu.Cuid].AuthRetries++
		log.Printf("Wrong password for user %s (%s)",
			pkg.Users[cu.Cuid].Name, streamId)
		cu.Cuid = -1
		return
	}

	if pkg.Users[cu.Cuid].Authd == "" {
		if prevCuid != -1 {
			pkg.Users[prevCuid].Authd = ""
		}
		pkg.Users[cu.Cuid].Authd = streamId
		pkg.Users[cu.Cuid].AuthRetries = 0
		log.Printf("User %s authd (%s)",
			pkg.Users[cu.Cuid].Name, streamId)
		return
	}
}

func (cu *CurrentUser) HandleSudo(streamId string, event pkg.Event) {
	if cu.Cuid == -1 {
		return
	}
	if event.Passwd == pkg.Users[cu.Cuid].Passwd {
		log.Printf("Accepted sudo on user %s (%s)",
			pkg.Users[cu.Cuid].Name, streamId)
		return
	} else {
		log.Printf("Bad password for sudo on user %s (%s)",
			pkg.Users[cu.Cuid].Name, streamId)
		return
	}
}

func (cu *CurrentUser) HandlerDir(streamId string, event pkg.Event) {
	if cu.Cuid == -1 {
		return
	}
	log.Printf("Accepted dir on user %s (%s)",
		pkg.Users[cu.Cuid].Name, streamId)
}

func HandleStream(stream *pkg.Stream, wg *sync.WaitGroup) {
	defer wg.Done()
	cu := CurrentUser{
		Cuid: -1,
	}
	streamId := stream.StreamId
	for _, event := range stream.Events {
		if event.Type == "ssh" {
			cu.HandleSSH(streamId, event)
		}
		if event.Type == "sudo" {
			cu.HandleSudo(streamId, event)
		}
		if event.Type == "dir" {
			cu.HandlerDir(streamId, event)
		}
	}
}

func main() {
	file, err := os.Open("../data/streams5.txt")
	if err != nil {
		return
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	streams := pkg.ParseStreams(scanner)

	if err := scanner.Err(); err != nil {
		return
	}

	start := time.Now()

	var wg sync.WaitGroup
	for _, stream := range streams {
		wg.Add(1)
		go HandleStream(&stream, &wg)
	}
	wg.Wait()

	elapsed := time.Since(start).Nanoseconds()
	fmt.Printf("Обработка всех потоков заняла %d наносекунд\n", elapsed)
}
