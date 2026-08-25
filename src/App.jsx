import React, { useState, useEffect } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import './App.css';
import PaymentRequestForm from './PaymentRequestForm';
import ApprovalWorkflow from './ApprovalWorkflow';

const App = () => {
  const [activeTab, setActiveTab] = useState('dashboard');

  const [metrics, setMetrics] = useState({
    totalTransactions: '-',
    totalValue: '-',
    riskAlerts: '-',
  });

  const [recentTransactions, setRecentTransactions] = useState([]);

  // Data for the Bar Chart
  const [riskChartData, setRiskChartData] = useState([
    { name: 'Low Risk', count: 0, color: '#4caf50' },
    { name: 'Medium Risk', count: 0, color: '#ffeb3b' },
    { name: 'High Risk', count: 0, color: '#f44336' },
  ]);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        const response = await fetch('/api/dashboard');
        if (response.ok) {
          const data = await response.json();
          
          setMetrics({
            totalTransactions: data.total_transactions ?? '-',
            totalValue: data.total_value ?? '-',
            riskAlerts: data.risk_alerts ?? '-',
          });

          setRecentTransactions(data.recent_risky_transactions || data.recent_flagged_transactions || []);

          if (data.risk_distribution) {
            setRiskChartData([
              { name: 'Low Risk', count: data.risk_distribution.LOW || 0, color: '#4caf50' },
              { name: 'Medium Risk', count: data.risk_distribution.MEDIUM || 0, color: '#ffeb3b' },
              { name: 'High Risk', count: data.risk_distribution.HIGH || 0, color: '#f44336' },
            ]);
          }
        } else {
          console.error("Failed to fetch dashboard data");
        }
      } catch (error) {
        console.error("Error fetching dashboard data:", error);
      }
    };

    if (activeTab === 'dashboard') {
      fetchDashboardData();
    }
  }, [activeTab]);

  const getStatusColor = (riskLevel) => {
    if (riskLevel === 'HIGH') return 'red';
    if (riskLevel === 'MEDIUM') return 'yellow';
    if (riskLevel === 'LOW') return 'green';
    return 'gray';
  };

  return (
    <div className="dashboard-container">
      <header className="dashboard-header">
        <div className="header-content">
          <h1>
            FINSIGHT{' '}
            <span className="subtitle">
              | FINANCIAL INTELLIGENCE DASHBOARD
            </span>
          </h1>

          <nav className="top-nav">
            <button
              className={`nav-btn ${
                activeTab === 'dashboard' ? 'active' : ''
              }`}
              onClick={() => setActiveTab('dashboard')}
            >
              Dashboard
            </button>

            <button
              className={`nav-btn ${
                activeTab === 'request' ? 'active' : ''
              }`}
              onClick={() => setActiveTab('request')}
            >
              Submit Request
            </button>

            <button
              className={`nav-btn ${
                activeTab === 'approve' ? 'active' : ''
              }`}
              onClick={() => setActiveTab('approve')}
            >
              Review & Approve
            </button>
          </nav>
        </div>
      </header>

      <main className="dashboard-content">
        {activeTab === 'dashboard' && (
          <>
            {/* Top Metrics Section */}
            <section className="metrics-grid">
              <div className="metric-card">
                <h3 className="metric-title">Total Transactions</h3>
                <p className="metric-value">
                  {metrics.totalTransactions}
                </p>
              </div>

              <div className="metric-card">
                <h3 className="metric-title">Total Value</h3>
                <p className="metric-value text-blue">
                  {metrics.totalValue}
                </p>
              </div>

              <div className="metric-card">
                <h3 className="metric-title">Risk Alerts</h3>
                <p className="metric-value text-red">
                  {metrics.riskAlerts}
                </p>
              </div>
            </section>

            {/* Charts & Visualizations Section */}
            <section className="charts-section">
              <div className="chart-card">
                <h3 className="section-title">
                  Risk Distribution Chart
                </h3>

                <div className="chart-wrapper">
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart
                      data={riskChartData}
                      margin={{
                        top: 20,
                        right: 30,
                        left: 20,
                        bottom: 5,
                      }}
                    >
                      <CartesianGrid
                        strokeDasharray="3 3"
                        stroke="#444"
                      />

                      <XAxis
                        dataKey="name"
                        stroke="#ccc"
                      />

                      <YAxis stroke="#ccc" />

                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#222',
                          borderColor: '#444',
                          color: '#fff',
                        }}
                        itemStyle={{
                          color: '#fff',
                        }}
                      />

                      <Bar
                        dataKey="count"
                        radius={[4, 4, 0, 0]}
                      >
                        {riskChartData.map((entry, index) => (
                          <Cell
                            key={`cell-${index}`}
                            fill={entry.color}
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </section>

            {/* Table Section */}
            <section className="transactions-section">
              <div className="table-card">
                <h3 className="section-title">
                  Recent Flagged Transactions
                </h3>

                <div className="table-responsive">
                  <table className="transactions-table">
                    <thead>
                      <tr>
                        <th>Request ID</th>
                        <th>Vendor ID</th>
                        <th>Account ID</th>
                        <th>Amount</th>
                        <th>Location</th>
                        <th>Timestamp</th>
                        <th>Risk Score</th>
                        <th>Risk Level</th>
                        <th>Risk Reasons</th>
                        <th>Final Decision</th>
                      </tr>
                    </thead>

                    <tbody>
                      {recentTransactions.length > 0 ? (
                        recentTransactions.map((tx) => (
                          <tr key={tx.request_id}>
                            <td className="font-mono">
                              {tx.request_id}
                            </td>

                            <td className="font-mono">
                              {tx.vendor_id}
                            </td>

                            <td className="font-mono">
                              {tx.account_id}
                            </td>

                            <td className="font-mono">
                              {tx.amount}
                            </td>

                            <td>{tx.location}</td>

                            <td className="font-mono">
                              {tx.timestamp}
                            </td>

                            <td className="font-mono">
                              {tx.risk_score}
                            </td>

                            <td>
                              <span
                                className={`badge badge-${getStatusColor(tx.risk_level)}`}
                              >
                                <span
                                  className={`dot ${getStatusColor(tx.risk_level)}`}
                                ></span>{' '}
                                {tx.risk_level}
                              </span>
                            </td>

                            <td>{Array.isArray(tx.risk_reasons) ? tx.risk_reasons.join(', ') : tx.risk_reasons}</td>

                            <td>{tx.final_decision}</td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td colSpan="10" style={{ textAlign: 'center', padding: '2rem', color: '#888' }}>
                            No recent high-risk transactions found.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </section>
          </>
        )}

        {activeTab === 'request' && <PaymentRequestForm />}

        {activeTab === 'approve' && <ApprovalWorkflow />}
      </main>
    </div>
  );
};

export default App;