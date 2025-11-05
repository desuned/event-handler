package main

import (
	"bufio"
	"bytes"
	"encoding/json"
	"flag"
	"fmt"
	"go-data-handler/models"
	"go-data-handler/pkg"
	"log"
	"net/http"
	"os"
)

func main() {
	filename := flag.String("file", "./data/streams5.txt", "Путь к файлу с данными")
	flag.Parse()

	file, err := os.Open(*filename)
	if err != nil {
		log.Fatal(err)
		return
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	streams := pkg.ParseStreams(scanner)

	if err := scanner.Err(); err != nil {
		log.Fatal(err)
		return
	}

	for _, stream := range streams {
		err := sendStreamToProcessor(stream)
		if err != nil {
			log.Printf("Failed to send stream %s: %v", stream.StreamId, err)
		} else {
			log.Printf("Successfully sent stream %s", stream.StreamId)
		}
	}

	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(streams)
	})

	http.ListenAndServe(":8080", nil)
}

func sendStreamToProcessor(stream models.Stream) error {
	targetURL := "http://localhost:8081/"

	jsonData, err := json.Marshal(stream)
	if err != nil {
		return fmt.Errorf("failed to marshal stream: %v", err)
	}

	resp, err := http.Post(targetURL, "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		return fmt.Errorf("failed to send request: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("processor returned status: %d", resp.StatusCode)
	}

	return nil
}
