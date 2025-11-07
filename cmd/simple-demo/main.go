package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"
)

const version = "1.0.0"

func main() {
	log.Println("🚀 Starting AFOC Platform Demo Server...")
	log.Printf("📍 Version: %s\n", version)
	log.Println("🌐 Server will start on http://localhost:8080")

	mux := http.NewServeMux()
	setupRoutes(mux)

	server := &http.Server{
		Addr:    ":8080",
		Handler: mux,
	}

	go func() {
		log.Println("\n✅ Server is running!")
		log.Println("📊 Dashboard: http://localhost:8080/dashboard")
		log.Println("🔗 Health Check: http://localhost:8080/health")
		log.Println("\nPress Ctrl+C to stop\n")

		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatal(err)
		}
	}()

	// Wait for interrupt
	stop := make(chan os.Signal, 1)
	signal.Notify(stop, syscall.SIGINT, syscall.SIGTERM)
	<-stop

	log.Println("\n🛑 Shutting down server...")
	server.Close()
	log.Println("✅ Server stopped")
}

func setupRoutes(mux *http.ServeMux) {
	mux.HandleFunc("/", handleDashboard)
	mux.HandleFunc("/dashboard", handleDashboard)
	mux.HandleFunc("/health", handleHealth)
	mux.HandleFunc("/api/metrics", handleMetrics)
	mux.HandleFunc("/api/resources", handleResources)
	mux.HandleFunc("/api/predictions", handlePredictions)
	mux.HandleFunc("/api/recommendations", handleRecommendations)
	mux.HandleFunc("/api/costs", handleCosts)
	mux.HandleFunc("/api/anomalies", handleAnomalies)
}

func handleHealth(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"status":    "healthy",
		"version":   version,
		"timestamp": time.Now().Format(time.RFC3339),
		"service":   "afoc-platform",
	})
}

func handleMetrics(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	metrics := []map[string]interface{}{
		{
			"resource_id":   "prod-web-server-01",
			"resource_type": "compute",
			"metric_name":   "cpu_usage",
			"value":         45.5,
			"unit":          "percent",
			"timestamp":     time.Now().Format(time.RFC3339),
			"provider":      "aws",
			"region":        "us-east-1",
		},
		{
			"resource_id":   "prod-web-server-01",
			"metric_name":   "memory_usage",
			"value":         62.3,
			"unit":          "percent",
			"timestamp":     time.Now().Format(time.RFC3339),
		},
		{
			"resource_id":   "prod-database-01",
			"metric_name":   "connections",
			"value":         45,
			"unit":          "count",
			"timestamp":     time.Now().Format(time.RFC3339),
		},
	}

	json.NewEncoder(w).Encode(map[string]interface{}{
		"status":           "success",
		"metrics_collected": len(metrics),
		"provider":         "demo",
		"metrics":          metrics,
	})
}

func handleResources(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	resources := []map[string]interface{}{
		{
			"id":       "prod-web-server-01",
			"name":     "Production Web Server",
			"type":     "compute",
			"provider": "aws",
			"region":   "us-east-1",
			"state":    "running",
			"cost": map[string]interface{}{
				"hourly_cost":  0.50,
				"daily_cost":   12.00,
				"monthly_cost": 360.00,
				"currency":     "USD",
			},
			"tags": map[string]string{
				"environment": "production",
				"team":        "platform",
			},
		},
		{
			"id":       "prod-database-01",
			"name":     "Production Database",
			"type":     "database",
			"provider": "aws",
			"region":   "us-east-1",
			"state":    "running",
			"cost": map[string]interface{}{
				"monthly_cost": 250.00,
				"currency":     "USD",
			},
		},
	}

	json.NewEncoder(w).Encode(map[string]interface{}{
		"status":    "success",
		"count":     len(resources),
		"resources": resources,
	})
}

func handlePredictions(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

	predictions := []map[string]interface{}{}
	baseValue := 1250.0

	for i := 1; i <= 7; i++ {
		trend := baseValue * (1.0 + float64(i)*0.01)
		predictions = append(predictions, map[string]interface{}{
			"date":           time.Now().AddDate(0, 0, i).Format("2006-01-02"),
			"predicted_cost": fmt.Sprintf("%.2f", trend),
			"lower_bound":    fmt.Sprintf("%.2f", trend*0.9),
			"upper_bound":    fmt.Sprintf("%.2f", trend*1.1),
		})
	}

	json.NewEncoder(w).Encode(map[string]interface{}{
		"status":            "success",
		"forecast_days":     7,
		"confidence_score":  0.85,
		"model_type":        "prophet",
		"predictions":       predictions,
		"generated_at":      time.Now().Format(time.RFC3339),
	})
}

func handleRecommendations(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	recommendations := []map[string]interface{}{
		{
			"id":                       "rec-001",
			"resource_id":              "prod-web-server-01",
			"resource_name":            "Production Web Server",
			"action_type":              "rightsize",
			"description":              "Instance has low CPU utilization (8.5%). Recommend downsizing from t3.xlarge to t3.large to save costs.",
			"estimated_monthly_savings": 45.50,
			"confidence_score":         0.92,
			"risk_level":               "low",
			"status":                   "pending",
		},
		{
			"id":                       "rec-002",
			"resource_id":              "analytics-cluster",
			"resource_name":            "Analytics Processing Cluster",
			"action_type":              "migrate_to_spot",
			"description":              "Non-critical batch workload suitable for spot instances. Potential 70% cost savings.",
			"estimated_monthly_savings": 280.00,
			"confidence_score":         0.78,
			"risk_level":               "medium",
			"status":                   "pending",
		},
		{
			"id":                       "rec-003",
			"resource_id":              "dev-database-02",
			"resource_name":            "Development Database",
			"action_type":              "stop",
			"description":              "Development resource unused outside business hours. Schedule shutdown 6PM-8AM weekdays.",
			"estimated_monthly_savings": 120.00,
			"confidence_score":         0.95,
			"risk_level":               "low",
			"status":                   "pending",
		},
	}

	json.NewEncoder(w).Encode(map[string]interface{}{
		"status":                  "success",
		"total_recommendations":   len(recommendations),
		"total_potential_savings": 445.50,
		"recommendations":         recommendations,
	})
}

func handleCosts(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"status":      "success",
		"total_cost":  1250.45,
		"currency":    "USD",
		"period":      "monthly",
		"cost_by_service": map[string]float64{
			"Compute":  850.30,
			"Storage":  200.15,
			"Network":  150.00,
			"Database": 50.00,
		},
		"cost_by_region": map[string]float64{
			"us-east-1": 750.25,
			"us-west-2": 500.20,
		},
		"savings_achieved": 28.5,
	})
}

func handleAnomalies(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	anomalies := []map[string]interface{}{
		{
			"id":            "anom-001",
			"resource_id":   "prod-api-gateway",
			"metric_name":   "cost",
			"actual_value":  1850.00,
			"expected_value": 950.00,
			"anomaly_score": 0.95,
			"severity":      "critical",
			"type":          "cost_spike",
			"detected_at":   time.Now().Add(-30 * time.Minute).Format(time.RFC3339),
			"root_cause": map[string]interface{}{
				"primary_cause":        "Unusual traffic spike detected - 300% increase in API calls",
				"contributing_factors": []string{"increased_api_calls", "high_data_transfer", "peak_hour_usage"},
				"confidence":           0.88,
			},
			"suggested_actions": []map[string]interface{}{
				{
					"action":      "Enable auto-scaling to handle traffic spikes",
					"confidence":  0.90,
					"auto_executable": false,
				},
				{
					"action":      "Implement request caching to reduce API calls",
					"confidence":  0.85,
					"auto_executable": false,
				},
			},
		},
	}

	json.NewEncoder(w).Encode(map[string]interface{}{
		"status":           "success",
		"active_anomalies": len(anomalies),
		"anomalies":        anomalies,
	})
}

func handleDashboard(w http.ResponseWriter, r *http.Request) {
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
        .pulse {
            animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: .5; }
        }
    </style>
</head>
<body class="bg-gray-50">
    <div class="min-h-screen">
        <!-- Header -->
        <header class="gradient-bg text-white shadow-lg">
            <div class="max-w-7xl mx-auto px-4 py-8">
                <div class="flex items-center justify-between">
                    <div>
                        <h1 class="text-5xl font-bold">🚀 AFOC Platform</h1>
                        <p class="text-2xl mt-2 opacity-90">Autonomous Fleet Optimization & Control</p>
                        <p class="mt-2 opacity-75 text-lg">AI-Powered Multi-Cloud Cost Optimization | Version ` + version + `</p>
                    </div>
                    <div class="text-right">
                        <div class="inline-flex items-center bg-green-500 text-white px-4 py-2 rounded-full">
                            <span class="pulse mr-2">●</span>
                            <span class="font-semibold">System Healthy</span>
                        </div>
                    </div>
                </div>
            </div>
        </header>

        <!-- Main Content -->
        <main class="max-w-7xl mx-auto px-4 py-8">
            <!-- Status Cards -->
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                <div class="bg-white rounded-xl shadow-lg p-6 transform hover:scale-105 transition-transform">
                    <div class="flex items-center justify-between mb-2">
                        <div class="text-sm font-semibold text-gray-600">Monthly Cost</div>
                        <div class="text-2xl">💰</div>
                    </div>
                    <div class="text-4xl font-bold text-gray-900">$1,250</div>
                    <div class="text-sm text-green-600 font-semibold mt-2 flex items-center">
                        <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6"></path>
                        </svg>
                        ↓ 28% savings this month
                    </div>
                </div>

                <div class="bg-white rounded-xl shadow-lg p-6 transform hover:scale-105 transition-transform">
                    <div class="flex items-center justify-between mb-2">
                        <div class="text-sm font-semibold text-gray-600">Active Resources</div>
                        <div class="text-2xl">☁️</div>
                    </div>
                    <div class="text-4xl font-bold text-gray-900">142</div>
                    <div class="text-sm text-blue-600 font-semibold mt-2">
                        Across AWS, GCP, Azure
                    </div>
                </div>

                <div class="bg-white rounded-xl shadow-lg p-6 transform hover:scale-105 transition-transform">
                    <div class="flex items-center justify-between mb-2">
                        <div class="text-sm font-semibold text-gray-600">Recommendations</div>
                        <div class="text-2xl">💡</div>
                    </div>
                    <div class="text-4xl font-bold text-gray-900">12</div>
                    <div class="text-sm text-purple-600 font-semibold mt-2">
                        $445 potential savings
                    </div>
                </div>

                <div class="bg-white rounded-xl shadow-lg p-6 transform hover:scale-105 transition-transform">
                    <div class="flex items-center justify-between mb-2">
                        <div class="text-sm font-semibold text-gray-600">System Uptime</div>
                        <div class="text-2xl">✅</div>
                    </div>
                    <div class="text-4xl font-bold text-green-600">99.94%</div>
                    <div class="text-sm text-gray-600 font-semibold mt-2">
                        Last 30 days
                    </div>
                </div>
            </div>

            <!-- API Endpoints -->
            <div class="bg-white rounded-xl shadow-lg p-8 mb-8">
                <h2 class="text-3xl font-bold text-gray-900 mb-6 flex items-center">
                    <span class="mr-3">📡</span>
                    Live API Endpoints
                </h2>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div class="flex items-center justify-between p-4 bg-gradient-to-r from-blue-50 to-blue-100 rounded-lg hover:shadow-md transition-shadow">
                        <div>
                            <code class="text-sm font-mono font-semibold text-blue-900">GET /api/metrics</code>
                            <p class="text-xs text-gray-600 mt-1">Real-time resource metrics</p>
                        </div>
                        <a href="/api/metrics" target="_blank" class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-semibold transition-colors">
                            Test →
                        </a>
                    </div>

                    <div class="flex items-center justify-between p-4 bg-gradient-to-r from-green-50 to-green-100 rounded-lg hover:shadow-md transition-shadow">
                        <div>
                            <code class="text-sm font-mono font-semibold text-green-900">GET /api/resources</code>
                            <p class="text-xs text-gray-600 mt-1">Multi-cloud resource inventory</p>
                        </div>
                        <a href="/api/resources" target="_blank" class="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg text-sm font-semibold transition-colors">
                            Test →
                        </a>
                    </div>

                    <div class="flex items-center justify-between p-4 bg-gradient-to-r from-purple-50 to-purple-100 rounded-lg hover:shadow-md transition-shadow">
                        <div>
                            <code class="text-sm font-mono font-semibold text-purple-900">GET /api/predictions</code>
                            <p class="text-xs text-gray-600 mt-1">AI cost forecasts (7-30 days)</p>
                        </div>
                        <a href="/api/predictions" target="_blank" class="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg text-sm font-semibold transition-colors">
                            Test →
                        </a>
                    </div>

                    <div class="flex items-center justify-between p-4 bg-gradient-to-r from-yellow-50 to-yellow-100 rounded-lg hover:shadow-md transition-shadow">
                        <div>
                            <code class="text-sm font-mono font-semibold text-yellow-900">GET /api/recommendations</code>
                            <p class="text-xs text-gray-600 mt-1">Actionable cost optimizations</p>
                        </div>
                        <a href="/api/recommendations" target="_blank" class="bg-yellow-600 hover:bg-yellow-700 text-white px-4 py-2 rounded-lg text-sm font-semibold transition-colors">
                            Test →
                        </a>
                    </div>

                    <div class="flex items-center justify-between p-4 bg-gradient-to-r from-red-50 to-red-100 rounded-lg hover:shadow-md transition-shadow">
                        <div>
                            <code class="text-sm font-mono font-semibold text-red-900">GET /api/anomalies</code>
                            <p class="text-xs text-gray-600 mt-1">Real-time anomaly detection</p>
                        </div>
                        <a href="/api/anomalies" target="_blank" class="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg text-sm font-semibold transition-colors">
                            Test →
                        </a>
                    </div>

                    <div class="flex items-center justify-between p-4 bg-gradient-to-r from-indigo-50 to-indigo-100 rounded-lg hover:shadow-md transition-shadow">
                        <div>
                            <code class="text-sm font-mono font-semibold text-indigo-900">GET /api/costs</code>
                            <p class="text-xs text-gray-600 mt-1">Cost breakdown & analysis</p>
                        </div>
                        <a href="/api/costs" target="_blank" class="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg text-sm font-semibold transition-colors">
                            Test →
                        </a>
                    </div>
                </div>
            </div>

            <!-- Features Grid -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                <div class="bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl shadow-lg p-8 text-white">
                    <div class="text-5xl mb-4">🔮</div>
                    <h3 class="text-2xl font-bold mb-3">Predictive Intelligence</h3>
                    <ul class="space-y-2">
                        <li class="flex items-center">
                            <svg class="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path>
                            </svg>
                            AI/ML forecasting (7-30 days ahead)
                        </li>
                        <li class="flex items-center">
                            <svg class="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path>
                            </svg>
                            85%+ prediction accuracy (Prophet models)
                        </li>
                        <li class="flex items-center">
                            <svg class="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path>
                            </svg>
                            Cost trends & usage pattern analysis
                        </li>
                    </ul>
                </div>

                <div class="bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl shadow-lg p-8 text-white">
                    <div class="text-5xl mb-4">🤖</div>
                    <h3 class="text-2xl font-bold mb-3">Autonomous Orchestration</h3>
                    <ul class="space-y-2">
                        <li class="flex items-center">
                            <svg class="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path>
                            </svg>
                            Proactive auto-scaling (before spikes)
                        </li>
                        <li class="flex items-center">
                            <svg class="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path>
                            </svg>
                            Automated rightsizing & spot migration
                        </li>
                        <li class="flex items-center">
                            <svg class="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path>
                            </svg>
                            Idle resource shutdown (with safety checks)
                        </li>
                    </ul>
                </div>

                <div class="bg-gradient-to-br from-green-500 to-green-600 rounded-xl shadow-lg p-8 text-white">
                    <div class="text-5xl mb-4">☁️</div>
                    <h3 class="text-2xl font-bold mb-3">Multi-Cloud Native</h3>
                    <ul class="space-y-2">
                        <li class="flex items-center">
                            <svg class="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path>
                            </svg>
                            AWS, GCP, Azure (unified API)
                        </li>
                        <li class="flex items-center">
                            <svg class="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path>
                            </svg>
                            Kubernetes (EKS, GKE, AKS) integration
                        </li>
                        <li class="flex items-center">
                            <svg class="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path>
                            </svg>
                            Zero vendor lock-in architecture
                        </li>
                    </ul>
                </div>

                <div class="bg-gradient-to-br from-red-500 to-red-600 rounded-xl shadow-lg p-8 text-white">
                    <div class="text-5xl mb-4">🔧</div>
                    <h3 class="text-2xl font-bold mb-3">Self-Healing</h3>
                    <ul class="space-y-2">
                        <li class="flex items-center">
                            <svg class="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path>
                            </svg>
                            Real-time anomaly detection (cost spikes)
                        </li>
                        <li class="flex items-center">
                            <svg class="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path>
                            </svg>
                            Automated root cause analysis (RCA)
                        </li>
                        <li class="flex items-center">
                            <svg class="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path>
                            </svg>
                            Automated remediation (restarts, rollbacks)
                        </li>
                    </ul>
                </div>
            </div>

            <!-- Technology Stack -->
            <div class="bg-white rounded-xl shadow-lg p-8">
                <h2 class="text-3xl font-bold text-gray-900 mb-6 flex items-center">
                    <span class="mr-3">⚡</span>
                    Technology Stack
                </h2>
                <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div class="p-4 bg-blue-50 rounded-xl text-center border-2 border-blue-200">
                        <div class="text-3xl mb-2">🐹</div>
                        <div class="font-bold text-gray-900">Backend</div>
                        <div class="text-sm text-gray-600 mt-1">Go 1.21</div>
                    </div>
                    <div class="p-4 bg-green-50 rounded-xl text-center border-2 border-green-200">
                        <div class="text-3xl mb-2">🐍</div>
                        <div class="font-bold text-gray-900">ML/AI</div>
                        <div class="text-sm text-gray-600 mt-1">Python 3.11</div>
                    </div>
                    <div class="p-4 bg-purple-50 rounded-xl text-center border-2 border-purple-200">
                        <div class="text-3xl mb-2">📬</div>
                        <div class="font-bold text-gray-900">Messaging</div>
                        <div class="text-sm text-gray-600 mt-1">NATS JetStream</div>
                    </div>
                    <div class="p-4 bg-yellow-50 rounded-xl text-center border-2 border-yellow-200">
                        <div class="text-3xl mb-2">🗄️</div>
                        <div class="font-bold text-gray-900">Database</div>
                        <div class="text-sm text-gray-600 mt-1">PostgreSQL + TimescaleDB</div>
                    </div>
                </div>
            </div>
        </main>

        <!-- Footer -->
        <footer class="bg-gray-900 text-white mt-12 py-8">
            <div class="max-w-7xl mx-auto px-4 text-center">
                <p class="text-lg font-semibold">Built by Oracle | Principal Multi-Cloud & AI Systems Architect</p>
                <p class="text-sm text-gray-400 mt-2">AFOC Platform v` + version + ` | Enterprise-Grade Autonomous Cloud Optimization</p>
                <p class="text-xs text-gray-500 mt-2">Running on Port 8080 | ` + time.Now().Format("2006-01-02") + `</p>
            </div>
        </footer>
    </div>
</body>
</html>`

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.Write([]byte(html))
}
