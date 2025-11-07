package main

import (
	"fmt"
	"log"
	"net/http"

	"github.com/afoc/services/internal/handlers"
	"github.com/gorilla/mux"
)

func main() {
	r := mux.NewRouter()

	r.HandleFunc("/health", handlers.HealthCheckHandler).Methods("GET")
	r.HandleFunc("/api/status", handlers.StatusHandler).Methods("GET")

	port := "8080"
	fmt.Printf("Server starting on port %s\n", port)

	if err := http.ListenAndServe(":"+port, r); err != nil {
		log.Fatal(err)
	}
}
