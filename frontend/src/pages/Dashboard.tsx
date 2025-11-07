import { useQuery } from '@tanstack/react-query';
import { LineChart, Line, AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { CloudIcon, CurrencyDollarIcon, ServerIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline';
import { MetricCard } from '../components/MetricCard';
import { api } from '../lib/api';

export function Dashboard() {
  const { data: metrics, isLoading } = useQuery({
    queryKey: ['dashboard-metrics'],
    queryFn: api.getDashboardMetrics,
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  const { data: predictions } = useQuery({
    queryKey: ['cost-predictions'],
    queryFn: api.getCostPredictions,
  });

  const { data: anomalies } = useQuery({
    queryKey: ['recent-anomalies'],
    queryFn: () => api.getAnomalies({ limit: 10 }),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Cloud Orchestration Dashboard</h1>
        <p className="mt-2 text-gray-600">
          Real-time multi-cloud cost optimization and resource management
        </p>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Total Monthly Cost"
          value={`$${metrics?.totalCost.toLocaleString() || 0}`}
          change={metrics?.costChange || 0}
          icon={CurrencyDollarIcon}
          trend="down"
        />
        <MetricCard
          title="Active Resources"
          value={metrics?.activeResources || 0}
          change={metrics?.resourceChange || 0}
          icon={ServerIcon}
          trend="up"
        />
        <MetricCard
          title="Cloud Providers"
          value={metrics?.cloudProviders || 3}
          icon={CloudIcon}
        />
        <MetricCard
          title="Active Anomalies"
          value={anomalies?.length || 0}
          change={-15}
          icon={ExclamationTriangleIcon}
          trend="down"
          variant="warning"
        />
      </div>

      {/* Cost Trend Chart */}
      <div className="bg-white rounded-lg shadow-lg p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">
          Cost Trend & Predictions (30 Days)
        </h2>
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={predictions?.dailyData || []}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip
              formatter={(value: number) => [`$${value.toFixed(2)}`, 'Cost']}
            />
            <Legend />
            <Area
              type="monotone"
              dataKey="actual"
              stroke="#2563eb"
              fill="#3b82f6"
              name="Actual Cost"
            />
            <Area
              type="monotone"
              dataKey="predicted"
              stroke="#10b981"
              fill="#34d399"
              fillOpacity={0.3}
              name="Predicted Cost"
            />
            <Area
              type="monotone"
              dataKey="upperBound"
              stroke="#f59e0b"
              fill="none"
              strokeDasharray="5 5"
              name="Upper Bound"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Resource Utilization */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Resource Utilization by Provider
          </h2>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={metrics?.utilizationByProvider || []}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="provider" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="cpu" fill="#3b82f6" name="CPU %" />
              <Bar dataKey="memory" fill="#10b981" name="Memory %" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-white rounded-lg shadow-lg p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Cost by Service (This Month)
          </h2>
          <div className="space-y-3">
            {metrics?.costByService?.map((service: any) => (
              <div key={service.name} className="flex items-center justify-between">
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-gray-700">{service.name}</span>
                    <span className="text-sm font-semibold text-gray-900">
                      ${service.cost.toFixed(2)}
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full"
                      style={{ width: `${service.percentage}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Recent Anomalies */}
      <div className="bg-white rounded-lg shadow-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900">Recent Anomalies</h2>
          <a href="/anomalies" className="text-blue-600 hover:text-blue-700 text-sm font-medium">
            View all
          </a>
        </div>
        <div className="space-y-3">
          {anomalies?.slice(0, 5).map((anomaly: any) => (
            <div
              key={anomaly.id}
              className="flex items-center justify-between p-3 bg-red-50 rounded-lg border border-red-200"
            >
              <div>
                <p className="text-sm font-medium text-gray-900">{anomaly.title}</p>
                <p className="text-xs text-gray-600">{anomaly.resource}</p>
              </div>
              <div className="text-right">
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                  anomaly.severity === 'critical' ? 'bg-red-100 text-red-800' : 'bg-yellow-100 text-yellow-800'
                }`}>
                  {anomaly.severity}
                </span>
                <p className="text-xs text-gray-500 mt-1">{anomaly.timestamp}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
