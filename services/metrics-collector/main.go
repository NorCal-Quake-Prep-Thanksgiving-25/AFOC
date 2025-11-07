package main

import (
	"context"
	"fmt"
	"net"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/afoc/platform/pkg/cloud"
	"github.com/afoc/platform/pkg/cloud/aws"
	"github.com/afoc/platform/pkg/cloud/gcp"
	"github.com/afoc/platform/pkg/cloud/kubernetes"
	metricsv1 "github.com/afoc/platform/proto/gen/metrics/v1"
	"github.com/nats-io/nats.go"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/trace"
	"go.uber.org/zap"
	"google.golang.org/grpc"
	"google.golang.org/protobuf/types/known/timestamppb"
	"gorm.io/driver/postgres"
	"gorm.io/gorm"
)

const (
	serviceName    = "metrics-collector"
	serviceVersion = "1.0.0"
)

type server struct {
	metricsv1.UnimplementedMetricsServiceServer
	providers map[string]cloud.Provider
	db        *gorm.DB
	nats      *nats.Conn
	logger    *zap.Logger
	tracer    trace.Tracer
}

func main() {
	logger, _ := zap.NewProduction()
	defer logger.Sync()

	logger.Info("Starting Metrics Collector Service", zap.String("version", serviceVersion))

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	// Initialize database
	db, err := initDatabase()
	if err != nil {
		logger.Fatal("Failed to initialize database", zap.Error(err))
	}

	// Initialize NATS connection
	nc, err := initNATS()
	if err != nil {
		logger.Fatal("Failed to initialize NATS", zap.Error(err))
	}
	defer nc.Close()

	// Initialize cloud providers
	providers := initProviders(ctx, logger)

	// Initialize tracer
	tracer := otel.Tracer(serviceName)

	// Create gRPC server
	srv := &server{
		providers: providers,
		db:        db,
		nats:      nc,
		logger:    logger,
		tracer:    tracer,
	}

	grpcServer := grpc.NewServer()
	metricsv1.RegisterMetricsServiceServer(grpcServer, srv)

	// Start background metrics collection
	go srv.runPeriodicCollection(ctx)

	// Start gRPC server
	lis, err := net.Listen("tcp", ":8080")
	if err != nil {
		logger.Fatal("Failed to listen", zap.Error(err))
	}

	go func() {
		logger.Info("gRPC server listening", zap.String("address", lis.Addr().String()))
		if err := grpcServer.Serve(lis); err != nil {
			logger.Fatal("Failed to serve", zap.Error(err))
		}
	}()

	// Wait for shutdown signal
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
	<-sigChan

	logger.Info("Shutting down gracefully")
	grpcServer.GracefulStop()
}

func (s *server) CollectMetrics(ctx context.Context, req *metricsv1.CollectMetricsRequest) (*metricsv1.CollectMetricsResponse, error) {
	ctx, span := s.tracer.Start(ctx, "CollectMetrics")
	defer span.End()

	s.logger.Info("Collecting metrics",
		zap.String("provider", req.Provider),
		zap.String("account_id", req.AccountId))

	provider, ok := s.providers[req.Provider]
	if !ok {
		return nil, fmt.Errorf("unknown provider: %s", req.Provider)
	}

	// Collect metrics from provider
	metricsReq := &cloud.MetricsRequest{
		StartTime:   time.Now().Add(-1 * time.Hour),
		EndTime:     time.Now(),
		Granularity: 5 * time.Minute,
	}

	resp, err := provider.CollectMetrics(ctx, metricsReq)
	if err != nil {
		s.logger.Error("Failed to collect metrics", zap.Error(err))
		return nil, err
	}

	// Store metrics in database
	for _, metric := range resp.Metrics {
		if err := s.storeMetric(metric); err != nil {
			s.logger.Error("Failed to store metric", zap.Error(err))
		}
	}

	// Publish metrics to NATS for real-time processing
	s.publishMetrics(resp.Metrics)

	return &metricsv1.CollectMetricsResponse{
		MetricsCollected: int32(len(resp.Metrics)),
		CollectionTime:   timestamppb.New(resp.CollectedAt),
		JobId:            fmt.Sprintf("job-%d", time.Now().Unix()),
	}, nil
}

func (s *server) GetMetrics(ctx context.Context, req *metricsv1.GetMetricsRequest) (*metricsv1.GetMetricsResponse, error) {
	ctx, span := s.tracer.Start(ctx, "GetMetrics")
	defer span.End()

	// Query metrics from TimescaleDB
	var metrics []MetricDB
	query := s.db.Where("resource_id = ? AND metric_name = ?", req.ResourceId, req.MetricName)

	if req.StartTime != nil {
		query = query.Where("timestamp >= ?", req.StartTime.AsTime())
	}
	if req.EndTime != nil {
		query = query.Where("timestamp <= ?", req.EndTime.AsTime())
	}

	if err := query.Find(&metrics).Error; err != nil {
		return nil, err
	}

	points := make([]*metricsv1.MetricPoint, len(metrics))
	for i, m := range metrics {
		points[i] = &metricsv1.MetricPoint{
			ResourceId:   m.ResourceID,
			ResourceType: m.ResourceType,
			MetricName:   m.MetricName,
			Value:        m.Value,
			Unit:         m.Unit,
			Timestamp:    timestamppb.New(m.Timestamp),
			Provider:     m.Provider,
			Region:       m.Region,
		}
	}

	return &metricsv1.GetMetricsResponse{Points: points}, nil
}

func (s *server) StreamMetrics(req *metricsv1.StreamMetricsRequest, stream metricsv1.MetricsService_StreamMetricsServer) error {
	// Subscribe to NATS stream for real-time metrics
	sub, err := s.nats.Subscribe("metrics.*", func(msg *nats.Msg) {
		// Parse and send metrics to client
		// In production: unmarshal protobuf and filter by req.ResourceIds
	})
	if err != nil {
		return err
	}
	defer sub.Unsubscribe()

	<-stream.Context().Done()
	return nil
}

func (s *server) runPeriodicCollection(ctx context.Context) {
	ticker := time.NewTicker(5 * time.Minute)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			s.logger.Info("Running periodic metrics collection")
			for providerName, provider := range s.providers {
				req := &cloud.MetricsRequest{
					StartTime:   time.Now().Add(-10 * time.Minute),
					EndTime:     time.Now(),
					Granularity: 1 * time.Minute,
				}

				resp, err := provider.CollectMetrics(ctx, req)
				if err != nil {
					s.logger.Error("Periodic collection failed",
						zap.String("provider", providerName),
						zap.Error(err))
					continue
				}

				s.logger.Info("Collected metrics",
					zap.String("provider", providerName),
					zap.Int("count", len(resp.Metrics)))

				for _, metric := range resp.Metrics {
					s.storeMetric(metric)
				}
			}
		}
	}
}

func (s *server) storeMetric(metric *cloud.Metric) error {
	m := MetricDB{
		ResourceID:   metric.ResourceID,
		ResourceType: metric.ResourceType,
		MetricName:   metric.MetricName,
		Value:        metric.Value,
		Unit:         metric.Unit,
		Timestamp:    metric.Timestamp,
		Provider:     metric.Provider,
		Region:       metric.Region,
	}
	return s.db.Create(&m).Error
}

func (s *server) publishMetrics(metrics []*cloud.Metric) {
	for _, m := range metrics {
		subject := fmt.Sprintf("metrics.%s.%s", m.Provider, m.MetricName)
		// In production: marshal to protobuf
		s.nats.Publish(subject, []byte(m.ResourceID))
	}
}

// MetricDB represents the database model for metrics
type MetricDB struct {
	ID           uint      `gorm:"primaryKey"`
	ResourceID   string    `gorm:"index"`
	ResourceType string    `gorm:"index"`
	MetricName   string    `gorm:"index"`
	Value        float64
	Unit         string
	Timestamp    time.Time `gorm:"index"`
	Provider     string    `gorm:"index"`
	Region       string
}

func initDatabase() (*gorm.DB, error) {
	dsn := getEnv("DATABASE_URL", "host=localhost user=afoc password=afoc dbname=afoc port=5432 sslmode=disable")
	db, err := gorm.Open(postgres.Open(dsn), &gorm.Config{})
	if err != nil {
		return nil, err
	}

	// Auto-migrate schema
	db.AutoMigrate(&MetricDB{})

	// Enable TimescaleDB hypertable (if TimescaleDB extension is available)
	db.Exec("SELECT create_hypertable('metric_dbs', 'timestamp', if_not_exists => TRUE)")

	return db, nil
}

func initNATS() (*nats.Conn, error) {
	natsURL := getEnv("NATS_URL", "nats://localhost:4222")
	return nats.Connect(natsURL)
}

func initProviders(ctx context.Context, logger *zap.Logger) map[string]cloud.Provider {
	providers := make(map[string]cloud.Provider)

	// AWS Provider
	if awsProvider, err := aws.NewProvider(ctx, "us-east-1", logger); err == nil {
		providers["aws"] = awsProvider
	} else {
		logger.Warn("Failed to initialize AWS provider", zap.Error(err))
	}

	// GCP Provider
	if gcpProvider, err := gcp.NewProvider(ctx, "my-project", "us-central1", logger); err == nil {
		providers["gcp"] = gcpProvider
	} else {
		logger.Warn("Failed to initialize GCP provider", zap.Error(err))
	}

	// Kubernetes Provider
	if k8sProvider, err := kubernetes.NewProvider(ctx, "", "default", logger); err == nil {
		providers["kubernetes"] = k8sProvider
	} else {
		logger.Warn("Failed to initialize Kubernetes provider", zap.Error(err))
	}

	return providers
}

func getEnv(key, fallback string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return fallback
}
