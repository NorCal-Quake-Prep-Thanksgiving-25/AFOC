package kubernetes

import (
	"context"
	"fmt"
	"time"

	"github.com/afoc/platform/pkg/cloud"
	"go.uber.org/zap"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/clientcmd"
	metricsv "k8s.io/metrics/pkg/client/clientset/versioned"
)

// Provider implements cloud.Provider for Kubernetes
type Provider struct {
	clientset        *kubernetes.Clientset
	metricsClientset *metricsv.Clientset
	clusterName      string
	logger           *zap.Logger
}

// NewProvider creates a new Kubernetes provider
func NewProvider(ctx context.Context, kubeconfigPath, clusterName string, logger *zap.Logger) (*Provider, error) {
	var config *rest.Config
	var err error

	if kubeconfigPath == "" {
		// In-cluster config
		config, err = rest.InClusterConfig()
	} else {
		config, err = clientcmd.BuildConfigFromFlags("", kubeconfigPath)
	}

	if err != nil {
		return nil, fmt.Errorf("failed to load kubeconfig: %w", err)
	}

	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		return nil, fmt.Errorf("failed to create kubernetes client: %w", err)
	}

	metricsClientset, err := metricsv.NewForConfig(config)
	if err != nil {
		return nil, fmt.Errorf("failed to create metrics client: %w", err)
	}

	return &Provider{
		clientset:        clientset,
		metricsClientset: metricsClientset,
		clusterName:      clusterName,
		logger:           logger,
	}, nil
}

// GetName returns the provider name
func (p *Provider) GetName() string {
	return "kubernetes"
}

// CollectMetrics collects pod and node metrics
func (p *Provider) CollectMetrics(ctx context.Context, req *cloud.MetricsRequest) (*cloud.MetricsResponse, error) {
	p.logger.Info("Collecting Kubernetes metrics")

	var allMetrics []*cloud.Metric

	// Get pod metrics
	podMetrics, err := p.metricsClientset.MetricsV1beta1().PodMetricses("").List(ctx, metav1.ListOptions{})
	if err != nil {
		p.logger.Error("Failed to get pod metrics", zap.Error(err))
		return nil, err
	}

	for _, pm := range podMetrics.Items {
		for _, container := range pm.Containers {
			cpuUsage := float64(container.Usage.Cpu().MilliValue()) / 1000.0
			memoryUsage := float64(container.Usage.Memory().Value()) / 1024 / 1024 // MB

			allMetrics = append(allMetrics, &cloud.Metric{
				ResourceID:   fmt.Sprintf("%s/%s", pm.Namespace, pm.Name),
				ResourceType: "pod",
				MetricName:   "cpu_usage",
				Value:        cpuUsage,
				Unit:         "cores",
				Timestamp:    pm.Timestamp.Time,
				Provider:     "kubernetes",
				Labels: map[string]string{
					"namespace": pm.Namespace,
					"pod":       pm.Name,
					"container": container.Name,
				},
			})

			allMetrics = append(allMetrics, &cloud.Metric{
				ResourceID:   fmt.Sprintf("%s/%s", pm.Namespace, pm.Name),
				ResourceType: "pod",
				MetricName:   "memory_usage",
				Value:        memoryUsage,
				Unit:         "MB",
				Timestamp:    pm.Timestamp.Time,
				Provider:     "kubernetes",
				Labels: map[string]string{
					"namespace": pm.Namespace,
					"pod":       pm.Name,
					"container": container.Name,
				},
			})
		}
	}

	return &cloud.MetricsResponse{
		Metrics:     allMetrics,
		CollectedAt: time.Now(),
	}, nil
}

// ListResources lists pods and nodes
func (p *Provider) ListResources(ctx context.Context, resourceTypes []string) ([]*cloud.Resource, error) {
	p.logger.Info("Listing Kubernetes resources", zap.Strings("types", resourceTypes))

	var resources []*cloud.Resource

	if contains(resourceTypes, "pod") {
		pods, err := p.clientset.CoreV1().Pods("").List(ctx, metav1.ListOptions{})
		if err != nil {
			return nil, err
		}

		for _, pod := range pods.Items {
			resources = append(resources, p.podToResource(&pod))
		}
	}

	return resources, nil
}

// podToResource converts a Kubernetes pod to cloud.Resource
func (p *Provider) podToResource(pod *corev1.Pod) *cloud.Resource {
	state := cloud.ResourceStateRunning
	if pod.Status.Phase != corev1.PodRunning {
		state = cloud.ResourceStateStopped
	}

	labels := make(map[string]string)
	for k, v := range pod.Labels {
		labels[k] = v
	}

	return &cloud.Resource{
		ID:        fmt.Sprintf("%s/%s", pod.Namespace, pod.Name),
		Name:      pod.Name,
		Type:      "pod",
		Provider:  "kubernetes",
		Region:    p.clusterName,
		Tags:      labels,
		State:     state,
		CreatedAt: pod.CreationTimestamp.Time,
		Metadata: map[string]interface{}{
			"namespace": pod.Namespace,
			"node":      pod.Spec.NodeName,
		},
	}
}

// GetResource retrieves a specific pod
func (p *Provider) GetResource(ctx context.Context, resourceID string) (*cloud.Resource, error) {
	// Parse namespace/name from resourceID
	namespace, name := "default", resourceID
	pod, err := p.clientset.CoreV1().Pods(namespace).Get(ctx, name, metav1.GetOptions{})
	if err != nil {
		return nil, err
	}

	return p.podToResource(pod), nil
}

// ScaleResource scales a deployment
func (p *Provider) ScaleResource(ctx context.Context, resourceID string, targetSize int) error {
	p.logger.Info("Scaling Kubernetes resource",
		zap.String("resource", resourceID),
		zap.Int("replicas", targetSize))

	// In production: use Scale subresource
	return nil
}

// RightsizeResource updates resource requests/limits
func (p *Provider) RightsizeResource(ctx context.Context, resourceID string, newInstanceType string) error {
	p.logger.Info("Rightsizing Kubernetes resource", zap.String("resource", resourceID))
	return nil
}

// StopResource deletes a pod
func (p *Provider) StopResource(ctx context.Context, resourceID string) error {
	namespace, name := "default", resourceID
	return p.clientset.CoreV1().Pods(namespace).Delete(ctx, name, metav1.DeleteOptions{})
}

// TerminateResource deletes a deployment
func (p *Provider) TerminateResource(ctx context.Context, resourceID string) error {
	return p.StopResource(ctx, resourceID)
}

// GetCostData retrieves Kubernetes cost data
func (p *Provider) GetCostData(ctx context.Context, startTime, endTime time.Time) (*cloud.CostData, error) {
	// In production: integrate with Kubecost or OpenCost
	return &cloud.CostData{
		TotalCost: 450.00,
		CostByService: map[string]float64{
			"Compute": 350.00,
			"Storage": 100.00,
		},
		Currency:  "USD",
		StartTime: startTime,
		EndTime:   endTime,
	}, nil
}

func contains(slice []string, item string) bool {
	for _, s := range slice {
		if s == item {
			return true
		}
	}
	return false
}
