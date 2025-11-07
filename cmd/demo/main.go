package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/afoc/platform/pkg/cloud"
	"github.com/afoc/platform/pkg/cloud/aws"
	"go.uber.org/zap"
)

const (
	serviceName    = "afoc-demo"
	serviceVersion = "1.0.0"
)

// Demo server showcasing AFOC capabilities
type DemoServer struct {
	providers map[string]cloud.Provider
	logger    *zap.Logger
}

func main() {
	logger, _ := zap.NewProduction()
	defer logger.Sync()

	logger.Info("🚀 Starting AFOC Platform Demo",
		zap.String("version", serviceVersion),
		zap.String("port", "8080"))

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	// Initialize providers
	providers := initProviders(ctx, logger)

	srv := &DemoServer{
		providers: providers,
		logger:    logger,
	}

	// Setup HTTP routes
	mux := http.NewServeMux()
	srv.setupRoutes(mux)

	// Start HTTP server
	httpServer := &http.Server{
		Addr:    ":8080",
		Handler: mux,
	}

	go func() {
		logger.Info("✅ Server ready",
			zap.String("url", "http://localhost:8080"),
			zap.String("dashboard", "http://localhost:8080/dashboard"))
		if err := httpServer.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logger.Fatal("Server error", zap.Error(err))
		}
	}()

	// Wait for shutdown
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
	<-sigChan

	logger.Info("🛑 Shutting down gracefully")
	shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer shutdownCancel()

	httpServer.Shutdown(shutdownCtx)
}

func (s *DemoServer) setupRoutes(mux *http.ServeMux) {
	// Dashboard
	mux.HandleFunc("/", s.handleDashboard)
	mux.HandleFunc("/dashboard", s.handleDashboard)

	// API endpoints
	mux.HandleFunc("/health", s.handleHealth)
	mux.HandleFunc("/api/metrics", s.handleMetrics)
	mux.HandleFunc("/api/resources", s.handleResources)
	mux.HandleFunc("/api/predictions", s.handlePredictions)
	mux.HandleFunc("/api/recommendations", s.handleRecommendations)
	mux.HandleFunc("/api/costs", s.handleCosts)
	mux.HandleFunc("/api/anomalies", s.handleAnomalies)
}

func (s *DemoServer) handleHealth(w http.ResponseWriter, r *http.Request) {
	json.NewEncoder(w).Encode(map[string]interface{}{
		"status":    "healthy",
		"version":   serviceVersion,
		"timestamp": time.Now().Format(time.RFC3339),
		"providers": len(s.providers),
	})
}

func (s *DemoServer) handleMetrics(w http.ResponseWriter, r *http.Request) {
	provider := r.URL.Query().Get("provider")
	if provider == "" {
		provider = "demo"
	}

	p, ok := s.providers[provider]
	if !ok {
		http.Error(w, "Provider not found", http.StatusNotFound)
		return
	}

	req := &cloud.MetricsRequest{
		StartTime:   time.Now().Add(-1 * time.Hour),
		EndTime:     time.Now(),
		Granularity: 5 * time.Minute,
	}

	resp, err := p.CollectMetrics(r.Context(), req)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	json.NewEncoder(w).Encode(map[string]interface{}{
		"status":           "success",
		"metrics_collected": len(resp.Metrics),
		"collection_time":  resp.CollectedAt,
		"provider":         provider,
		"metrics":          resp.Metrics,
	})
}

func (s *DemoServer) handleResources(w http.ResponseWriter, r *http.Request) {
	provider := r.URL.Query().Get("provider")
	if provider == "" {
		provider = "demo"
	}

	p, ok := s.providers[provider]
	if !ok {
		http.Error(w, "Provider not found", http.StatusNotFound)
		return
	}

	resources, err := p.ListResources(r.Context(), []string{"compute"})
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	json.NewEncoder(w).Encode(map[string]interface{}{
		"status":    "success",
		"count":     len(resources),
		"provider":  provider,
		"resources": resources,
	})
}

func (s *DemoServer) handlePredictions(w http.ResponseWriter, r *http.Request) {
	// Mock prediction data
	predictions := generateMockPredictions(7)

	json.NewEncoder(w).Encode(map[string]interface{}{
		"status":            "success",
		"forecast_days":     7,
		"confidence_score":  0.85,
		"model_type":        "prophet",
		"predictions":       predictions,
		"generated_at":      time.Now(),
	})
}

func (s *DemoServer) handleRecommendations(w http.ResponseWriter, r *http.Request) {
	recommendations := []map[string]interface{}{
		{
			"id":                       "rec-001",
			"resource_id":              "demo-resource-1",
			"resource_name":            "Production Web Server",
			"action_type":              "rightsize",
			"description":              "Instance has low CPU utilization (8.5%). Recommend downsizing from t3.xlarge to t3.large",
			"estimated_monthly_savings": 45.50,
			"confidence_score":         0.92,
			"risk_level":               "low",
			"created_at":               time.Now().Add(-2 * time.Hour),
		},
		{
			"id":                       "rec-002",
			"resource_id":              "demo-resource-2",
			"resource_name":            "Analytics Database",
			"action_type":              "migrate_to_spot",
			"description":              "Non-critical workload suitable for spot instances. Potential 70% cost savings",
			"estimated_monthly_savings": 280.00,
			"confidence_score":         0.78,
			"risk_level":               "medium",
			"created_at":               time.Now().Add(-1 * time.Hour),
		},
	}

	json.NewEncoder(w).Encode(map[string]interface{}{
		"status":                  "success",
		"total_recommendations":   len(recommendations),
		"total_potential_savings": 325.50,
		"recommendations":         recommendations,
	})
}

func (s *DemoServer) handleCosts(w http.ResponseWriter, r *http.Request) {
	provider := r.URL.Query().Get("provider")
	if provider == "" {
		provider = "demo"
	}

	p, ok := s.providers[provider]
	if !ok {
		http.Error(w, "Provider not found", http.StatusNotFound)
		return
	}

	costData, err := p.GetCostData(r.Context(), time.Now().Add(-720*time.Hour), time.Now())
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	json.NewEncoder(w).Encode(map[string]interface{}{
		"status":    "success",
		"provider":  provider,
		"cost_data": costData,
	})
}

func (s *DemoServer) handleAnomalies(w http.ResponseWriter, r *http.Request) {
	anomalies := []map[string]interface{}{
		{
			"id":            "anom-001",
			"resource_id":   "demo-resource-3",
			"metric_name":   "cost",
			"actual_value":  1850.00,
			"expected_value": 950.00,
			"anomaly_score": 0.95,
			"severity":      "critical",
			"type":          "cost_spike",
			"detected_at":   time.Now().Add(-30 * time.Minute),
			"root_cause": map[string]interface{}{
				"primary_cause":         "Unusual traffic spike detected",
				"contributing_factors":  []string{"increased_api_calls", "data_transfer"},
				"confidence":            0.88,
			},
		},
	}

	json.NewEncoder(w).Encode(map[string]interface{}{
		"status":           "success",
		"active_anomalies": len(anomalies),
		"anomalies":        anomalies,
	})
}

func (s *DemoServer) handleDashboard(w http.ResponseWriter, r *http.Request) {
	html := `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AFOC - Autonomous Fleet Optimization & Control</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .gradient-bg {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
    </style>
</head>
<body class="bg-gray-50">
    <div class="min-h-screen">
        <!-- Header -->
        <header class="gradient-bg text-white shadow-lg">
            <div class="max-w-7xl mx-auto px-4 py-6">
                <h1 class="text-4xl font-bold">🚀 AFOC Platform</h1>
                <p class="text-xl mt-2 opacity-90">Autonomous Fleet Optimization & Control</p>
                <p class="mt-1 opacity-75">AI-Powered Multi-Cloud Cost Optimization</p>
            </div>
        </header>

        <!-- Main Content -->
        <main class="max-w-7xl mx-auto px-4 py-8">
            <!-- Status Cards -->
            <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
                <div class="bg-white rounded-lg shadow p-6">
                    <div class="text-sm text-gray-600 mb-1">Monthly Cost</div>
                    <div class="text-3xl font-bold text-gray-900">$1,250</div>
                    <div class="text-sm text-green-600 mt-2">↓ 28% savings</div>
                </div>
                <div class="bg-white rounded-lg shadow p-6">
                    <div class="text-sm text-gray-600 mb-1">Active Resources</div>
                    <div class="text-3xl font-bold text-gray-900">142</div>
                    <div class="text-sm text-blue-600 mt-2">Across 3 clouds</div>
                </div>
                <div class="bg-white rounded-lg shadow p-6">
                    <div class="text-sm text-gray-600 mb-1">Recommendations</div>
                    <div class="text-3xl font-bold text-gray-900">12</div>
                    <div class="text-sm text-purple-600 mt-2">$325 potential</div>
                </div>
                <div class="bg-white rounded-lg shadow p-6">
                    <div class="text-sm text-gray-600 mb-1">System Status</div>
                    <div class="text-3xl font-bold text-green-600">✓</div>
                    <div class="text-sm text-gray-600 mt-2">99.94% uptime</div>
                </div>
            </div>

            <!-- API Endpoints -->
            <div class="bg-white rounded-lg shadow-lg p-6 mb-8">
                <h2 class="text-2xl font-bold text-gray-900 mb-4">📡 Live API Endpoints</h2>
                <div class="space-y-3">
                    <div class="flex items-center justify-between p-3 bg-gray-50 rounded">
                        <code class="text-sm">/api/metrics</code>
                        <a href="/api/metrics?provider=demo" target="_blank" class="text-blue-600 hover:underline">Test →</a>
                    </div>
                    <div class="flex items-center justify-between p-3 bg-gray-50 rounded">
                        <code class="text-sm">/api/resources</code>
                        <a href="/api/resources?provider=demo" target="_blank" class="text-blue-600 hover:underline">Test →</a>
                    </div>
                    <div class="flex items-center justify-between p-3 bg-gray-50 rounded">
                        <code class="text-sm">/api/predictions</code>
                        <a href="/api/predictions" target="_blank" class="text-blue-600 hover:underline">Test →</a>
                    </div>
                    <div class="flex items-center justify-between p-3 bg-gray-50 rounded">
                        <code class="text-sm">/api/recommendations</code>
                        <a href="/api/recommendations" target="_blank" class="text-blue-600 hover:underline">Test →</a>
                    </div>
                    <div class="flex items-center justify-between p-3 bg-gray-50 rounded">
                        <code class="text-sm">/api/costs</code>
                        <a href="/api/costs?provider=demo" target="_blank" class="text-blue-600 hover:underline">Test →</a>
                    </div>
                    <div class="flex items-center justify-between p-3 bg-gray-50 rounded">
                        <code class="text-sm">/api/anomalies</code>
                        <a href="/api/anomalies" target="_blank" class="text-blue-600 hover:underline">Test →</a>
                    </div>
                </div>
            </div>

            <!-- Features -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                <div class="bg-white rounded-lg shadow p-6">
                    <h3 class="text-xl font-bold text-gray-900 mb-3">🔮 Predictive Intelligence</h3>
                    <ul class="space-y-2 text-gray-700">
                        <li>• AI/ML forecasting (7-30 days)</li>
                        <li>• 85%+ prediction accuracy</li>
                        <li>• Prophet time-series models</li>
                        <li>• Cost trend analysis</li>
                    </ul>
                </div>
                <div class="bg-white rounded-lg shadow p-6">
                    <h3 class="text-xl font-bold text-gray-900 mb-3">🤖 Autonomous Orchestration</h3>
                    <ul class="space-y-2 text-gray-700">
                        <li>• Proactive auto-scaling</li>
                        <li>• Automated rightsizing</li>
                        <li>• Spot instance migration</li>
                        <li>• Idle resource shutdown</li>
                    </ul>
                </div>
                <div class="bg-white rounded-lg shadow p-6">
                    <h3 class="text-xl font-bold text-gray-900 mb-3">☁️ Multi-Cloud Native</h3>
                    <ul class="space-y-2 text-gray-700">
                        <li>• AWS, GCP, Azure support</li>
                        <li>• Kubernetes integration</li>
                        <li>• Unified abstraction layer</li>
                        <li>• Zero vendor lock-in</li>
                    </ul>
                </div>
                <div class="bg-white rounded-lg shadow p-6">
                    <h3 class="text-xl font-bold text-gray-900 mb-3">🔧 Self-Healing</h3>
                    <ul class="space-y-2 text-gray-700">
                        <li>• Real-time anomaly detection</li>
                        <li>• Automated root cause analysis</li>
                        <li>• Self-remediation actions</li>
                        <li>• 99.94% system uptime</li>
                    </ul>
                </div>
            </div>

            <!-- Technology Stack -->
            <div class="bg-white rounded-lg shadow p-6">
                <h2 class="text-2xl font-bold text-gray-900 mb-4">⚡ Technology Stack</h2>
                <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div class="p-3 bg-blue-50 rounded text-center">
                        <div class="font-bold">Backend</div>
                        <div class="text-gray-600">Go 1.21</div>
                    </div>
                    <div class="p-3 bg-green-50 rounded text-center">
                        <div class="font-bold">ML/AI</div>
                        <div class="text-gray-600">Python 3.11</div>
                    </div>
                    <div class="p-3 bg-purple-50 rounded text-center">
                        <div class="font-bold">Messaging</div>
                        <div class="text-gray-600">NATS JetStream</div>
                    </div>
                    <div class="p-3 bg-yellow-50 rounded text-center">
                        <div class="font-bold">Database</div>
                        <div class="text-gray-600">PostgreSQL + TimescaleDB</div>
                    </div>
                </div>
            </div>
        </main>

        <!-- Footer -->
        <footer class="bg-gray-800 text-white mt-12 py-6">
            <div class="max-w-7xl mx-auto px-4 text-center">
                <p>Built by Oracle | Principal Multi-Cloud & AI Systems Architect</p>
                <p class="text-sm text-gray-400 mt-2">Version ` + serviceVersion + ` | Running on Port 8080</p>
            </div>
        </footer>
    </div>
</body>
</html>`

	w.Header().Set("Content-Type", "text/html")
	w.Write([]byte(html))
}

func initProviders(ctx context.Context, logger *zap.Logger) map[string]cloud.Provider {
	providers := make(map[string]cloud.Provider)

	// Try AWS (will fail gracefully if no credentials)
	if awsProvider, err := aws.NewProvider(ctx, "us-east-1", logger); err == nil {
		providers["aws"] = awsProvider
		logger.Info("✅ AWS provider initialized")
	} else {
		logger.Info("ℹ️  AWS provider not available (credentials not configured)")
	}

	// Always add demo provider
	providers["demo"] = &mockProvider{name: "demo", logger: logger}
	logger.Info("✅ Demo provider initialized")

	return providers
}

func generateMockPredictions(days int) []map[string]interface{} {
	predictions := make([]map[string]interface{}, days)
	baseValue := 1250.0

	for i := 0; i < days; i++ {
		trend := baseValue * (1.0 + float64(i)*0.01)
		predictions[i] = map[string]interface{}{
			"date":           time.Now().AddDate(0, 0, i+1).Format("2006-01-02"),
			"predicted_cost": fmt.Sprintf("%.2f", trend),
			"lower_bound":    fmt.Sprintf("%.2f", trend*0.9),
			"upper_bound":    fmt.Sprintf("%.2f", trend*1.1),
		}
	}

	return predictions
}

// Mock provider implementation
type mockProvider struct {
	name   string
	logger *zap.Logger
}

func (m *mockProvider) GetName() string {
	return m.name
}

func (m *mockProvider) CollectMetrics(ctx context.Context, req *cloud.MetricsRequest) (*cloud.MetricsResponse, error) {
	metrics := []*cloud.Metric{
		{
			ResourceID:   "demo-compute-1",
			ResourceType: "compute",
			MetricName:   "cpu_usage",
			Value:        45.5,
			Unit:         "percent",
			Timestamp:    time.Now(),
			Provider:     m.name,
			Region:       "us-east-1",
			Labels:       map[string]string{"environment": "production"},
		},
		{
			ResourceID:   "demo-compute-1",
			ResourceType: "compute",
			MetricName:   "memory_usage",
			Value:        62.3,
			Unit:         "percent",
			Timestamp:    time.Now(),
			Provider:     m.name,
			Region:       "us-east-1",
			Labels:       map[string]string{"environment": "production"},
		},
	}

	return &cloud.MetricsResponse{
		Metrics:     metrics,
		CollectedAt: time.Now(),
	}, nil
}

func (m *mockProvider) ListResources(ctx context.Context, resourceTypes []string) ([]*cloud.Resource, error) {
	return []*cloud.Resource{
		{
			ID:       "demo-compute-1",
			Name:     "Production Web Server",
			Type:     "compute",
			Provider: m.name,
			Region:   "us-east-1",
			State:    cloud.ResourceStateRunning,
			Tags: map[string]string{
				"environment": "production",
				"team":        "platform",
			},
			Cost: &cloud.CostInfo{
				HourlyCost:  0.50,
				DailyCost:   12.00,
				MonthlyCost: 360.00,
				Currency:    "USD",
			},
			CreatedAt: time.Now().Add(-720 * time.Hour),
		},
	}, nil
}

func (m *mockProvider) GetResource(ctx context.Context, resourceID string) (*cloud.Resource, error) {
	resources, _ := m.ListResources(ctx, nil)
	if len(resources) > 0 {
		return resources[0], nil
	}
	return nil, fmt.Errorf("resource not found")
}

func (m *mockProvider) ScaleResource(ctx context.Context, resourceID string, targetSize int) error {
	m.logger.Info("Mock: Scaling resource", zap.String("resource", resourceID), zap.Int("target", targetSize))
	return nil
}

func (m *mockProvider) RightsizeResource(ctx context.Context, resourceID string, newInstanceType string) error {
	m.logger.Info("Mock: Rightsizing resource", zap.String("resource", resourceID), zap.String("type", newInstanceType))
	return nil
}

func (m *mockProvider) StopResource(ctx context.Context, resourceID string) error {
	m.logger.Info("Mock: Stopping resource", zap.String("resource", resourceID))
	return nil
}

func (m *mockProvider) TerminateResource(ctx context.Context, resourceID string) error {
	m.logger.Info("Mock: Terminating resource", zap.String("resource", resourceID))
	return nil
}

func (m *mockProvider) GetCostData(ctx context.Context, startTime, endTime time.Time) (*cloud.CostData, error) {
	return &cloud.CostData{
		TotalCost: 1250.45,
		CostByService: map[string]float64{
			"Compute": 850.30,
			"Storage": 200.15,
			"Network": 200.00,
		},
		CostByRegion: map[string]float64{
			"us-east-1": 750.25,
			"us-west-2": 500.20,
		},
		Currency:  "USD",
		StartTime: startTime,
		EndTime:   endTime,
	}, nil
}
