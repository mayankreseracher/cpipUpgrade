package main

import (
	"context"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/mayankreseracher/cpipUpgrade/internal/logging"
	"github.com/mayankreseracher/cpipUpgrade/internal/metrics"
	"github.com/mayankreseracher/cpipUpgrade/pkg/autocheck"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

func main() {
	log := logging.NewLogger()
	defer func() {
		if err := log.Sync(); err != nil {
			fmt.Fprintf(os.Stderr, "failed to sync logger: %v\n", err)
		}
	}()

	log.Info("Starting cpipUpgrade service")

	// Initialize metrics
	metrics.Init()

	// Setup HTTP server
	mux := http.NewServeMux()

	// Health check endpoint
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		fmt.Fprintf(w, `{"status":"healthy","timestamp":"%s"}`+"\n", time.Now().UTC().Format(time.RFC3339))
	})

	// Metrics endpoint
	mux.Handle("/metrics", promhttp.Handler())

	// OpenAPI spec
	mux.HandleFunc("/openapi.yaml", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/yaml")
		w.WriteHeader(http.StatusOK)
		w.Write(openAPISpec)
	})

	// Items endpoint
	mux.HandleFunc("/items", handleItems)

	// Run optional autocheck if enabled
	if os.Getenv("AUTOCHECK") == "true" {
		log.Info("Running autocheck for vulnerabilities")
		if err := autocheck.Run(context.Background(), log); err != nil {
			log.Error("autocheck failed", err)
		}
	}

	// Setup HTTP server with timeout
	server := &http.Server{
		Addr:         ":5081",
		Handler:      mux,
		ReadTimeout:  15 * time.Second,
		WriteTimeout: 15 * time.Second,
		IdleTimeout:  60 * time.Second,
	}

	// Graceful shutdown
	go func() {
		sigChan := make(chan os.Signal, 1)
		signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
		<-sigChan
		log.Info("Shutting down server")
		ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		defer cancel()
		if err := server.Shutdown(ctx); err != nil {
			log.Error("shutdown error", err)
		}
	}()

	log.Info("HTTP server listening", "port", "5081")
	if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		log.Fatal("server error", err)
	}
}

func handleItems(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	fmt.Fprint(w, `[{"id":1,"name":"item1"},{"id":2,"name":"item2"}]\n`)
}

var openAPISpec = []byte(`openapi: 3.0.0
info:
  title: cpipUpgrade Service
  version: 1.0.0
  description: Cloud-Powered Package Virtualization Service
paths:
  /health:
    get:
      summary: Health check endpoint
      responses:
        '200':
          description: Service is healthy
  /metrics:
    get:
      summary: Prometheus metrics
      responses:
        '200':
          description: Prometheus metrics in text format
  /items:
    get:
      summary: List items
      responses:
        '200':
          description: List of items
`)
