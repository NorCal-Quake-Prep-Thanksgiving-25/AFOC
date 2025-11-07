package cloud

import (
	"context"
	"time"
)

// Provider defines the interface for cloud provider implementations
type Provider interface {
	// GetName returns the provider name (aws, gcp, azure, kubernetes)
	GetName() string

	// CollectMetrics collects metrics for the specified resources
	CollectMetrics(ctx context.Context, req *MetricsRequest) (*MetricsResponse, error)

	// ListResources lists all resources of the specified types
	ListResources(ctx context.Context, resourceTypes []string) ([]*Resource, error)

	// GetResource retrieves a specific resource by ID
	GetResource(ctx context.Context, resourceID string) (*Resource, error)

	// ScaleResource scales a resource up or down
	ScaleResource(ctx context.Context, resourceID string, targetSize int) error

	// RightsizeResource modifies resource instance type/size
	RightsizeResource(ctx context.Context, resourceID string, newInstanceType string) error

	// StopResource stops a running resource
	StopResource(ctx context.Context, resourceID string) error

	// TerminateResource terminates a resource
	TerminateResource(ctx context.Context, resourceID string) error

	// GetCostData retrieves cost information
	GetCostData(ctx context.Context, startTime, endTime time.Time) (*CostData, error)
}

// MetricsRequest contains parameters for metrics collection
type MetricsRequest struct {
	ResourceIDs   []string
	MetricNames   []string
	StartTime     time.Time
	EndTime       time.Time
	Granularity   time.Duration
}

// MetricsResponse contains collected metrics
type MetricsResponse struct {
	Metrics       []*Metric
	CollectedAt   time.Time
}

// Metric represents a single metric data point
type Metric struct {
	ResourceID    string
	ResourceType  string
	MetricName    string
	Value         float64
	Unit          string
	Timestamp     time.Time
	Labels        map[string]string
	Provider      string
	Region        string
}

// Resource represents a cloud resource
type Resource struct {
	ID            string
	Name          string
	Type          string
	Provider      string
	Region        string
	AccountID     string
	Tags          map[string]string
	State         ResourceState
	CreatedAt     time.Time
	Cost          *CostInfo
	Metadata      map[string]interface{}
}

// ResourceState represents the state of a resource
type ResourceState string

const (
	ResourceStateRunning    ResourceState = "running"
	ResourceStateStopped    ResourceState = "stopped"
	ResourceStateTerminated ResourceState = "terminated"
	ResourceStatePending    ResourceState = "pending"
)

// CostInfo contains cost information for a resource
type CostInfo struct {
	HourlyCost  float64
	DailyCost   float64
	MonthlyCost float64
	Currency    string
}

// CostData contains aggregated cost information
type CostData struct {
	TotalCost      float64
	CostByService  map[string]float64
	CostByRegion   map[string]float64
	CostByResource map[string]float64
	Currency       string
	StartTime      time.Time
	EndTime        time.Time
}

// ProviderFactory creates cloud provider instances
type ProviderFactory interface {
	CreateProvider(providerName string, config map[string]string) (Provider, error)
}
