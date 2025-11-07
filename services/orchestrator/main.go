package main

import (
	"context"
	"encoding/json"
	"fmt"
	"net"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/afoc/platform/pkg/cloud"
	"github.com/afoc/platform/pkg/cloud/aws"
	orchestrationv1 "github.com/afoc/platform/proto/gen/orchestration/v1"
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
	serviceName = "orchestrator"
	version     = "1.0.0"
)

type server struct {
	orchestrationv1.UnimplementedOrchestrationServiceServer
	providers map[string]cloud.Provider
	db        *gorm.DB
	nats      *nats.Conn
	logger    *zap.Logger
	tracer    trace.Tracer
}

type Recommendation struct {
	ID                      string                         `gorm:"primaryKey"`
	ResourceID              string                         `gorm:"index"`
	ResourceName            string
	ActionType              orchestrationv1.ActionType
	Description             string
	EstimatedMonthlySavings float64
	ConfidenceScore         float64
	RiskLevel               orchestrationv1.RiskLevel
	Parameters              string // JSON
	CreatedAt               time.Time
	Status                  string `gorm:"default:'pending'"`
}

func main() {
	logger, _ := zap.NewProduction()
	defer logger.Sync()

	logger.Info("Starting Orchestrator Service", zap.String("version", version))

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	db, err := initDatabase()
	if err != nil {
		logger.Fatal("Failed to initialize database", zap.Error(err))
	}

	nc, err := initNATS()
	if err != nil {
		logger.Fatal("Failed to initialize NATS", zap.Error(err))
	}
	defer nc.Close()

	providers := initProviders(ctx, logger)
	tracer := otel.Tracer(serviceName)

	srv := &server{
		providers: providers,
		db:        db,
		nats:      nc,
		logger:    logger,
		tracer:    tracer,
	}

	// Subscribe to prediction events
	go srv.subscribeToPredictions(ctx)

	// Start recommendation generation
	go srv.generateRecommendations(ctx)

	grpcServer := grpc.NewServer()
	orchestrationv1.RegisterOrchestrationServiceServer(grpcServer, srv)

	lis, err := net.Listen("tcp", ":8082")
	if err != nil {
		logger.Fatal("Failed to listen", zap.Error(err))
	}

	go func() {
		logger.Info("gRPC server listening", zap.String("address", lis.Addr().String()))
		if err := grpcServer.Serve(lis); err != nil {
			logger.Fatal("Failed to serve", zap.Error(err))
		}
	}()

	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
	<-sigChan

	logger.Info("Shutting down gracefully")
	grpcServer.GracefulStop()
}

func (s *server) ExecuteAction(ctx context.Context, req *orchestrationv1.ExecuteActionRequest) (*orchestrationv1.ExecuteActionResponse, error) {
	ctx, span := s.tracer.Start(ctx, "ExecuteAction")
	defer span.End()

	s.logger.Info("Executing orchestration action",
		zap.String("action_id", req.ActionId),
		zap.String("action_type", req.ActionType.String()),
		zap.String("resource_id", req.ResourceId),
		zap.Bool("dry_run", req.DryRun))

	if req.DryRun {
		return &orchestrationv1.ExecuteActionResponse{
			ActionId:          req.ActionId,
			Status:            orchestrationv1.ActionStatus_ACTION_STATUS_COMPLETED,
			Message:           "Dry run completed successfully",
			ExecutedAt:        timestamppb.Now(),
			EstimatedSavings:  125.50,
		}, nil
	}

	// Get provider from resource ID (simplified)
	provider := s.providers["aws"]
	if provider == nil {
		return nil, fmt.Errorf("provider not available")
	}

	var err error
	switch req.ActionType {
	case orchestrationv1.ActionType_ACTION_TYPE_SCALE_DOWN:
		targetSize := 1 // Parse from parameters
		err = provider.ScaleResource(ctx, req.ResourceId, targetSize)

	case orchestrationv1.ActionType_ACTION_TYPE_RIGHTSIZE:
		newType := req.Parameters["instance_type"]
		err = provider.RightsizeResource(ctx, req.ResourceId, newType)

	case orchestrationv1.ActionType_ACTION_TYPE_STOP:
		err = provider.StopResource(ctx, req.ResourceId)

	case orchestrationv1.ActionType_ACTION_TYPE_TERMINATE:
		err = provider.TerminateResource(ctx, req.ResourceId)

	case orchestrationv1.ActionType_ACTION_TYPE_MIGRATE_TO_SPOT:
		s.logger.Info("Migrating to spot instance", zap.String("resource", req.ResourceId))
		// Complex multi-step process in production

	default:
		return nil, fmt.Errorf("unknown action type: %v", req.ActionType)
	}

	if err != nil {
		s.logger.Error("Action execution failed", zap.Error(err))
		return &orchestrationv1.ExecuteActionResponse{
			ActionId:   req.ActionId,
			Status:     orchestrationv1.ActionStatus_ACTION_STATUS_FAILED,
			Message:    err.Error(),
			ExecutedAt: timestamppb.Now(),
		}, nil
	}

	// Publish action event to NATS
	s.publishActionEvent(req.ActionId, req.ActionType, req.ResourceId)

	return &orchestrationv1.ExecuteActionResponse{
		ActionId:          req.ActionId,
		Status:            orchestrationv1.ActionStatus_ACTION_STATUS_COMPLETED,
		Message:           "Action completed successfully",
		ExecutedAt:        timestamppb.Now(),
		EstimatedSavings:  150.00,
	}, nil
}

func (s *server) GetRecommendations(ctx context.Context, req *orchestrationv1.GetRecommendationsRequest) (*orchestrationv1.GetRecommendationsResponse, error) {
	ctx, span := s.tracer.Start(ctx, "GetRecommendations")
	defer span.End()

	s.logger.Info("Getting recommendations",
		zap.String("provider", req.Provider),
		zap.String("account", req.AccountId))

	var recommendations []Recommendation
	query := s.db.Where("status = ?", "pending")

	if req.Provider != "" {
		query = query.Where("resource_id LIKE ?", req.Provider+"%")
	}

	if req.MinSavingsThreshold > 0 {
		query = query.Where("estimated_monthly_savings >= ?", req.MinSavingsThreshold)
	}

	if err := query.Order("estimated_monthly_savings DESC").Find(&recommendations).Error; err != nil {
		return nil, err
	}

	protoRecs := make([]*orchestrationv1.Recommendation, len(recommendations))
	totalSavings := 0.0

	for i, rec := range recommendations {
		var params map[string]string
		json.Unmarshal([]byte(rec.Parameters), &params)

		protoRecs[i] = &orchestrationv1.Recommendation{
			Id:                      rec.ID,
			ResourceId:              rec.ResourceID,
			ResourceName:            rec.ResourceName,
			ActionType:              rec.ActionType,
			Description:             rec.Description,
			EstimatedMonthlySavings: rec.EstimatedMonthlySavings,
			ConfidenceScore:         rec.ConfidenceScore,
			RiskLevel:               rec.RiskLevel,
			Parameters:              params,
			CreatedAt:               timestamppb.New(rec.CreatedAt),
		}

		totalSavings += rec.EstimatedMonthlySavings
	}

	return &orchestrationv1.GetRecommendationsResponse{
		Recommendations:       protoRecs,
		TotalPotentialSavings: totalSavings,
	}, nil
}

func (s *server) ApproveAction(ctx context.Context, req *orchestrationv1.ApproveActionRequest) (*orchestrationv1.ApproveActionResponse, error) {
	ctx, span := s.tracer.Start(ctx, "ApproveAction")
	defer span.End()

	s.logger.Info("Approving action",
		zap.String("recommendation_id", req.RecommendationId),
		zap.Bool("approved", req.Approved),
		zap.String("approver", req.Approver))

	// Update recommendation status
	var rec Recommendation
	if err := s.db.First(&rec, "id = ?", req.RecommendationId).Error; err != nil {
		return nil, err
	}

	if req.Approved {
		rec.Status = "approved"
	} else {
		rec.Status = "rejected"
	}

	s.db.Save(&rec)

	status := orchestrationv1.ActionStatus_ACTION_STATUS_APPROVED
	if !req.Approved {
		status = orchestrationv1.ActionStatus_ACTION_STATUS_FAILED
	}

	return &orchestrationv1.ApproveActionResponse{
		ActionId: rec.ID,
		Status:   status,
	}, nil
}

func (s *server) generateRecommendations(ctx context.Context) {
	ticker := time.NewTicker(1 * time.Hour)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			s.logger.Info("Generating cost optimization recommendations")

			// Analyze resources across all providers
			for providerName, provider := range s.providers {
				resources, err := provider.ListResources(ctx, []string{"ec2-instance", "pod"})
				if err != nil {
					s.logger.Error("Failed to list resources",
						zap.String("provider", providerName),
						zap.Error(err))
					continue
				}

				// Analyze each resource for optimization opportunities
				for _, resource := range resources {
					s.analyzeResource(resource, provider)
				}
			}
		}
	}
}

func (s *server) analyzeResource(resource *cloud.Resource, provider cloud.Provider) {
	// Example: Detect idle instances (simplified)
	if resource.State == cloud.ResourceStateRunning {
		// Check if instance has low utilization (would fetch from metrics in production)
		cpuUtilization := 5.0 // Mock data

		if cpuUtilization < 10.0 {
			// Create recommendation to stop or downsize
			params, _ := json.Marshal(map[string]string{
				"current_type": "t3.large",
				"recommended_type": "t3.small",
			})

			rec := Recommendation{
				ID:                      fmt.Sprintf("rec-%d", time.Now().Unix()),
				ResourceID:              resource.ID,
				ResourceName:            resource.Name,
				ActionType:              orchestrationv1.ActionType_ACTION_TYPE_RIGHTSIZE,
				Description:             fmt.Sprintf("Instance has low CPU utilization (%.1f%%). Recommend downsizing to save costs.", cpuUtilization),
				EstimatedMonthlySavings: 45.50,
				ConfidenceScore:         0.85,
				RiskLevel:               orchestrationv1.RiskLevel_RISK_LEVEL_LOW,
				Parameters:              string(params),
				CreatedAt:               time.Now(),
				Status:                  "pending",
			}

			s.db.Create(&rec)
			s.logger.Info("Created recommendation", zap.String("resource", resource.ID))
		}
	}
}

func (s *server) subscribeToPredictions(ctx context.Context) {
	s.nats.Subscribe("predictions.cost_spike", func(msg *nats.Msg) {
		s.logger.Info("Received cost spike prediction", zap.String("data", string(msg.Data)))
		// Take proactive action based on prediction
	})
}

func (s *server) publishActionEvent(actionID string, actionType orchestrationv1.ActionType, resourceID string) {
	event := map[string]interface{}{
		"action_id":   actionID,
		"action_type": actionType.String(),
		"resource_id": resourceID,
		"timestamp":   time.Now(),
	}

	data, _ := json.Marshal(event)
	s.nats.Publish("actions.executed", data)
}

func initDatabase() (*gorm.DB, error) {
	dsn := os.Getenv("DATABASE_URL")
	if dsn == "" {
		dsn = "host=localhost user=afoc password=afoc dbname=afoc port=5432 sslmode=disable"
	}

	db, err := gorm.Open(postgres.Open(dsn), &gorm.Config{})
	if err != nil {
		return nil, err
	}

	db.AutoMigrate(&Recommendation{})
	return db, nil
}

func initNATS() (*nats.Conn, error) {
	natsURL := os.Getenv("NATS_URL")
	if natsURL == "" {
		natsURL = "nats://localhost:4222"
	}
	return nats.Connect(natsURL)
}

func initProviders(ctx context.Context, logger *zap.Logger) map[string]cloud.Provider {
	providers := make(map[string]cloud.Provider)

	if awsProvider, err := aws.NewProvider(ctx, "us-east-1", logger); err == nil {
		providers["aws"] = awsProvider
	}

	return providers
}
