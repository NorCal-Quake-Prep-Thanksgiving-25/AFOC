package handlers

import (
	"encoding/json"
	"net/http"
)

// HealthCheckHandler handles health check requests
func HealthCheckHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)

	response := map[string]string{
		"status": "healthy",
		"service": "afoc-services",
	}

	json.NewEncoder(w).Encode(response)
}

// StatusHandler handles status requests
func StatusHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)

	response := map[string]interface{}{
		"status": "running",
		"version": "1.0.0",
		"service": "afoc-services",
	}

	json.NewEncoder(w).Encode(response)
}
