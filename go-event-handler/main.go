package main

import (
	"article/events-handler/models"
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"net/http"
	"sync"
	"time"
)

type CurrentUser struct {
	Cuid int
}

func (cu *CurrentUser) HandleSSH(streamId string, event models.Event) {
	prevCuid := cu.Cuid
	for i := range models.Users {
		if event.Name == models.Users[i].Name {
			cu.Cuid = i
		}
	}

	if cu.Cuid == -1 {
		log.Printf("Couldn't find a user with a name %s (%s)",
			event.Name, streamId)
		return
	}

	models.Users[cu.Cuid].Mu.Lock()
	defer models.Users[cu.Cuid].Mu.Unlock()

	if models.Users[cu.Cuid].AuthStream == streamId {
		log.Printf("You are already logged in (%s)", streamId)
		return
	}

	if models.Users[cu.Cuid].AuthStream != "" {
		log.Printf("User %s already AuthStream from %s (%s)",
			models.Users[cu.Cuid].Name, models.Users[cu.Cuid].AuthStream, streamId)
		cu.Cuid = -1
		return
	}

	if models.Users[cu.Cuid].AuthRetries >= 3 {
		log.Printf("Can't access user %s, user is blocked (%s)",
			models.Users[cu.Cuid].Name, streamId)
		cu.Cuid = -1
		return
	}

	if event.Passwd != models.Users[cu.Cuid].Passwd {
		models.Users[cu.Cuid].AuthRetries++
		log.Printf("Wrong password for user %s (%s)",
			models.Users[cu.Cuid].Name, streamId)
		cu.Cuid = -1
		return
	}

	if models.Users[cu.Cuid].AuthStream == "" {
		if prevCuid != -1 {
			models.Users[prevCuid].AuthStream = ""
		}
		models.Users[cu.Cuid].AuthStream = streamId
		models.Users[cu.Cuid].AuthRetries = 0
		log.Printf("User %s AuthStream (%s)",
			models.Users[cu.Cuid].Name, streamId)
		return
	}
}

func (cu *CurrentUser) HandleSudo(streamId string, event models.Event) {
	if cu.Cuid == -1 {
		return
	}
	if event.Passwd == models.Users[cu.Cuid].Passwd {
		log.Printf("Accepted sudo on user %s (%s)",
			models.Users[cu.Cuid].Name, streamId)
		return
	} else {
		log.Printf("Bad password for sudo on user %s (%s)",
			models.Users[cu.Cuid].Name, streamId)
		return
	}
}

func (cu *CurrentUser) HandlerDir(streamId string, event models.Event) {
	if cu.Cuid == -1 {
		return
	}
	log.Printf("Accepted dir on user %s (%s)",
		models.Users[cu.Cuid].Name, streamId)
}

func HandleStream(stream *models.Stream) {
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

var (
	startTime    time.Time
	totalStreams int
	totalTime    time.Duration
	mu           sync.Mutex
	wg           sync.WaitGroup
	maxStreams   int
	doneChan     chan struct{}
)

func main() {
	maxStreams := flag.Int("max", 5, "Maximum number of streams to use")
	flag.Parse()

	totalStreams = 0
	doneChan = make(chan struct{})

	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")

		if r.Method != http.MethodPost {
			w.WriteHeader(http.StatusMethodNotAllowed)
			json.NewEncoder(w).Encode(map[string]string{"error": "Method not allowed"})
			return
		}

		var stream models.Stream
		if err := json.NewDecoder(r.Body).Decode(&stream); err != nil {
			w.WriteHeader(http.StatusBadRequest)
			json.NewEncoder(w).Encode(map[string]string{"error": "Invalid JSON"})
			return
		}

		mu.Lock()
		if totalStreams >= *maxStreams {
			mu.Unlock()
			w.WriteHeader(http.StatusTooManyRequests)
			json.NewEncoder(w).Encode(map[string]string{"error": "Maximum streams limit reached"})
			return
		}

		totalStreams++
		currentCount := totalStreams
		mu.Unlock()

		wg.Add(1)
		go processStream(stream)

		json.NewEncoder(w).Encode(map[string]string{
			"status":    "processing_started",
			"stream_id": stream.StreamId,
			"count":     fmt.Sprintf("%d/%d", currentCount, maxStreams),
		})

		if currentCount == *maxStreams {
			go func() {
				time.Sleep(100 * time.Millisecond)
				close(doneChan)
			}()
		}
	})

	server := &http.Server{Addr: ":8081"}

	go func() {
		fmt.Println("Server starting on :8081")
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			panic(err)
		}
	}()

	select {
	case <-doneChan:
		fmt.Println("Полное чистое время обработки горутин: ", totalTime.Microseconds())
		fmt.Println("Достигнут лимит потоков, завершаем работу...")
	case <-waitWithTimeout(30 * time.Minute):
		fmt.Println("Таймаут, завершаем работу...")
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	server.Shutdown(ctx)

	wg.Wait()
}

func waitWithTimeout(d time.Duration) chan struct{} {
	ch := make(chan struct{})
	go func() {
		time.Sleep(d)
		close(ch)
	}()
	return ch
}

func processStream(stream models.Stream) {
	defer wg.Done()

	start := time.Now()

	HandleStream(&stream)

	duration := time.Since(start)
	totalTime += duration
	fmt.Printf("Завершение потока %s за %v\n", stream.StreamId, duration)
}
