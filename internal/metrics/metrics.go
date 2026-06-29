package metrics

import (
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
)

var (
	httpRequestsTotal = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "http_requests_total",
			Help: "Total HTTP requests",
		},
		[]string{"method", "path"},
	)
)

func Init() {
	// Metrics are initialized via promauto
}

func RecordRequest(method, path string) {
	httpRequestsTotal.WithLabelValues(method, path).Inc()
}
