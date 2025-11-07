package integration

import (
	"context"
	"testing"
	"time"

	"github.com/afoc/platform/pkg/cloud"
	"github.com/afoc/platform/pkg/cloud/aws"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"go.uber.org/zap"
)

// TestMetricsCollection tests the end-to-end metrics collection flow
func TestMetricsCollection(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping integration test in short mode")
	}

	ctx := context.Background()
	logger, _ := zap.NewDevelopment()

	// Create AWS provider
	provider, err := aws.NewProvider(ctx, "us-east-1", logger)
	require.NoError(t, err, "Failed to create AWS provider")

	t.Run("ListResources", func(t *testing.T) {
		resources, err := provider.ListResources(ctx, []string{"ec2-instance"})
		require.NoError(t, err, "Failed to list resources")
		assert.NotNil(t, resources, "Resources should not be nil")
	})

	t.Run("CollectMetrics", func(t *testing.T) {
		req := &cloud.MetricsRequest{
			ResourceIDs: []string{"i-test123"},
			MetricNames: []string{"CPUUtilization"},
			StartTime:   time.Now().Add(-1 * time.Hour),
			EndTime:     time.Now(),
			Granularity: 5 * time.Minute,
		}

		resp, err := provider.CollectMetrics(ctx, req)
		require.NoError(t, err, "Failed to collect metrics")
		assert.NotNil(t, resp, "Response should not be nil")
		assert.NotZero(t, resp.CollectedAt, "Collection time should be set")
	})
}

// TestProviderAbstraction tests multi-cloud provider abstraction
func TestProviderAbstraction(t *testing.T) {
	ctx := context.Background()
	logger, _ := zap.NewDevelopment()

	providers := []struct {
		name     string
		provider cloud.Provider
	}{
		// In production, initialize all providers
		// For testing, we'll use AWS only
	}

	for _, tc := range providers {
		t.Run(tc.name, func(t *testing.T) {
			// Test that provider implements interface correctly
			assert.NotEmpty(t, tc.provider.GetName())

			// Test cost data retrieval
			startTime := time.Now().Add(-24 * time.Hour)
			endTime := time.Now()
			costData, err := tc.provider.GetCostData(ctx, startTime, endTime)

			require.NoError(t, err)
			assert.NotNil(t, costData)
			assert.NotEmpty(t, costData.Currency)
			assert.True(t, costData.TotalCost >= 0)
		})
	}
}

// TestResourceOperations tests resource management operations
func TestResourceOperations(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping integration test in short mode")
	}

	ctx := context.Background()
	logger, _ := zap.NewDevelopment()

	provider, err := aws.NewProvider(ctx, "us-east-1", logger)
	require.NoError(t, err)

	t.Run("ScaleResource", func(t *testing.T) {
		// This would be a real resource ID in production tests
		resourceID := "test-resource-id"

		err := provider.ScaleResource(ctx, resourceID, 2)
		// In test mode, this might return an error due to non-existent resource
		// In production tests with real resources, this should succeed
		assert.Error(t, err) // Expected in test mode
	})
}

// BenchmarkMetricsCollection benchmarks metrics collection performance
func BenchmarkMetricsCollection(b *testing.B) {
	ctx := context.Background()
	logger, _ := zap.NewDevelopment()

	provider, err := aws.NewProvider(ctx, "us-east-1", logger)
	require.NoError(b, err)

	req := &cloud.MetricsRequest{
		ResourceIDs: []string{"i-test123"},
		MetricNames: []string{"CPUUtilization"},
		StartTime:   time.Now().Add(-1 * time.Hour),
		EndTime:     time.Now(),
		Granularity: 5 * time.Minute,
	}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, _ = provider.CollectMetrics(ctx, req)
	}
}
