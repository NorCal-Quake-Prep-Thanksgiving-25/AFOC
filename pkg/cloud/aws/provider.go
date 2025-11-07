package aws

import (
	"context"
	"fmt"
	"time"

	"github.com/afoc/platform/pkg/cloud"
	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/cloudwatch"
	"github.com/aws/aws-sdk-go-v2/service/cloudwatch/types"
	"github.com/aws/aws-sdk-go-v2/service/ec2"
	ec2types "github.com/aws/aws-sdk-go-v2/service/ec2/types"
	"go.uber.org/zap"
)

// Provider implements cloud.Provider for AWS
type Provider struct {
	cfg            aws.Config
	ec2Client      *ec2.Client
	cwClient       *cloudwatch.Client
	region         string
	logger         *zap.Logger
}

// NewProvider creates a new AWS provider
func NewProvider(ctx context.Context, region string, logger *zap.Logger) (*Provider, error) {
	cfg, err := config.LoadDefaultConfig(ctx, config.WithRegion(region))
	if err != nil {
		return nil, fmt.Errorf("failed to load AWS config: %w", err)
	}

	return &Provider{
		cfg:       cfg,
		ec2Client: ec2.NewFromConfig(cfg),
		cwClient:  cloudwatch.NewFromConfig(cfg),
		region:    region,
		logger:    logger,
	}, nil
}

// GetName returns the provider name
func (p *Provider) GetName() string {
	return "aws"
}

// CollectMetrics collects CloudWatch metrics
func (p *Provider) CollectMetrics(ctx context.Context, req *cloud.MetricsRequest) (*cloud.MetricsResponse, error) {
	p.logger.Info("Collecting AWS metrics",
		zap.Int("resource_count", len(req.ResourceIDs)),
		zap.Int("metric_count", len(req.MetricNames)))

	var allMetrics []*cloud.Metric

	for _, resourceID := range req.ResourceIDs {
		for _, metricName := range req.MetricNames {
			metrics, err := p.getMetricData(ctx, resourceID, metricName, req.StartTime, req.EndTime)
			if err != nil {
				p.logger.Error("Failed to get metric data",
					zap.String("resource_id", resourceID),
					zap.String("metric", metricName),
					zap.Error(err))
				continue
			}
			allMetrics = append(allMetrics, metrics...)
		}
	}

	return &cloud.MetricsResponse{
		Metrics:     allMetrics,
		CollectedAt: time.Now(),
	}, nil
}

// getMetricData retrieves CloudWatch metric data
func (p *Provider) getMetricData(ctx context.Context, resourceID, metricName string, startTime, endTime time.Time) ([]*cloud.Metric, error) {
	// Extract instance ID from resource ID
	instanceID := resourceID // Simplified - in production, parse ARN

	input := &cloudwatch.GetMetricStatisticsInput{
		Namespace:  aws.String("AWS/EC2"),
		MetricName: aws.String(metricName),
		Dimensions: []types.Dimension{
			{
				Name:  aws.String("InstanceId"),
				Value: aws.String(instanceID),
			},
		},
		StartTime:  aws.Time(startTime),
		EndTime:    aws.Time(endTime),
		Period:     aws.Int32(300), // 5 minutes
		Statistics: []types.Statistic{types.StatisticAverage},
	}

	output, err := p.cwClient.GetMetricStatistics(ctx, input)
	if err != nil {
		return nil, fmt.Errorf("failed to get metric statistics: %w", err)
	}

	var metrics []*cloud.Metric
	for _, datapoint := range output.Datapoints {
		metrics = append(metrics, &cloud.Metric{
			ResourceID:   resourceID,
			ResourceType: "ec2-instance",
			MetricName:   metricName,
			Value:        *datapoint.Average,
			Unit:         string(datapoint.Unit),
			Timestamp:    *datapoint.Timestamp,
			Provider:     "aws",
			Region:       p.region,
			Labels: map[string]string{
				"instance_id": instanceID,
			},
		})
	}

	return metrics, nil
}

// ListResources lists EC2 instances
func (p *Provider) ListResources(ctx context.Context, resourceTypes []string) ([]*cloud.Resource, error) {
	p.logger.Info("Listing AWS resources", zap.Strings("types", resourceTypes))

	var resources []*cloud.Resource

	// List EC2 instances
	if contains(resourceTypes, "ec2-instance") {
		instances, err := p.listEC2Instances(ctx)
		if err != nil {
			return nil, err
		}
		resources = append(resources, instances...)
	}

	return resources, nil
}

// listEC2Instances lists all EC2 instances
func (p *Provider) listEC2Instances(ctx context.Context) ([]*cloud.Resource, error) {
	input := &ec2.DescribeInstancesInput{}
	output, err := p.ec2Client.DescribeInstances(ctx, input)
	if err != nil {
		return nil, fmt.Errorf("failed to describe instances: %w", err)
	}

	var resources []*cloud.Resource
	for _, reservation := range output.Reservations {
		for _, instance := range reservation.Instances {
			tags := make(map[string]string)
			for _, tag := range instance.Tags {
				if tag.Key != nil && tag.Value != nil {
					tags[*tag.Key] = *tag.Value
				}
			}

			state := mapInstanceState(instance.State.Name)

			resources = append(resources, &cloud.Resource{
				ID:        *instance.InstanceId,
				Name:      getTagValue(tags, "Name"),
				Type:      "ec2-instance",
				Provider:  "aws",
				Region:    p.region,
				Tags:      tags,
				State:     state,
				CreatedAt: *instance.LaunchTime,
				Metadata: map[string]interface{}{
					"instance_type": string(instance.InstanceType),
					"availability_zone": *instance.Placement.AvailabilityZone,
				},
			})
		}
	}

	return resources, nil
}

// GetResource retrieves a specific resource
func (p *Provider) GetResource(ctx context.Context, resourceID string) (*cloud.Resource, error) {
	input := &ec2.DescribeInstancesInput{
		InstanceIds: []string{resourceID},
	}

	output, err := p.ec2Client.DescribeInstances(ctx, input)
	if err != nil {
		return nil, fmt.Errorf("failed to describe instance: %w", err)
	}

	if len(output.Reservations) == 0 || len(output.Reservations[0].Instances) == 0 {
		return nil, fmt.Errorf("instance not found: %s", resourceID)
	}

	instance := output.Reservations[0].Instances[0]
	tags := make(map[string]string)
	for _, tag := range instance.Tags {
		if tag.Key != nil && tag.Value != nil {
			tags[*tag.Key] = *tag.Value
		}
	}

	return &cloud.Resource{
		ID:        *instance.InstanceId,
		Name:      getTagValue(tags, "Name"),
		Type:      "ec2-instance",
		Provider:  "aws",
		Region:    p.region,
		Tags:      tags,
		State:     mapInstanceState(instance.State.Name),
		CreatedAt: *instance.LaunchTime,
		Metadata: map[string]interface{}{
			"instance_type": string(instance.InstanceType),
		},
	}, nil
}

// ScaleResource scales an Auto Scaling Group
func (p *Provider) ScaleResource(ctx context.Context, resourceID string, targetSize int) error {
	p.logger.Info("Scaling resource",
		zap.String("resource_id", resourceID),
		zap.Int("target_size", targetSize))

	// In production: call Auto Scaling API
	return nil
}

// RightsizeResource changes instance type
func (p *Provider) RightsizeResource(ctx context.Context, resourceID string, newInstanceType string) error {
	p.logger.Info("Rightsizing resource",
		zap.String("resource_id", resourceID),
		zap.String("new_type", newInstanceType))

	// In production: stop instance, modify instance type, start instance
	return nil
}

// StopResource stops an EC2 instance
func (p *Provider) StopResource(ctx context.Context, resourceID string) error {
	input := &ec2.StopInstancesInput{
		InstanceIds: []string{resourceID},
	}

	_, err := p.ec2Client.StopInstances(ctx, input)
	if err != nil {
		return fmt.Errorf("failed to stop instance: %w", err)
	}

	p.logger.Info("Stopped instance", zap.String("instance_id", resourceID))
	return nil
}

// TerminateResource terminates an EC2 instance
func (p *Provider) TerminateResource(ctx context.Context, resourceID string) error {
	input := &ec2.TerminateInstancesInput{
		InstanceIds: []string{resourceID},
	}

	_, err := p.ec2Client.TerminateInstances(ctx, input)
	if err != nil {
		return fmt.Errorf("failed to terminate instance: %w", err)
	}

	p.logger.Info("Terminated instance", zap.String("instance_id", resourceID))
	return nil
}

// GetCostData retrieves AWS Cost Explorer data
func (p *Provider) GetCostData(ctx context.Context, startTime, endTime time.Time) (*cloud.CostData, error) {
	// In production: use AWS Cost Explorer API
	// For now, return mock data
	return &cloud.CostData{
		TotalCost: 1250.45,
		CostByService: map[string]float64{
			"EC2": 850.30,
			"S3":  200.15,
			"RDS": 200.00,
		},
		Currency:  "USD",
		StartTime: startTime,
		EndTime:   endTime,
	}, nil
}

// Helper functions

func mapInstanceState(state ec2types.InstanceStateName) cloud.ResourceState {
	switch state {
	case ec2types.InstanceStateNameRunning:
		return cloud.ResourceStateRunning
	case ec2types.InstanceStateNameStopped:
		return cloud.ResourceStateStopped
	case ec2types.InstanceStateNameTerminated:
		return cloud.ResourceStateTerminated
	case ec2types.InstanceStateNamePending:
		return cloud.ResourceStatePending
	default:
		return cloud.ResourceStateStopped
	}
}

func getTagValue(tags map[string]string, key string) string {
	if val, ok := tags[key]; ok {
		return val
	}
	return ""
}

func contains(slice []string, item string) bool {
	for _, s := range slice {
		if s == item {
			return true
		}
	}
	return false
}
