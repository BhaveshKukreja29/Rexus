import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import './App.css';

const API_URL = 'http://localhost:8000/analytics';
const WS_URL = 'ws://localhost:8000/ws/logs';

const COLORS = { success: '#28a745', clientError: '#ffc107', serverError: '#dc3545' };

function App() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const response = await fetch(API_URL);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const result = await response.json();
        setData(result);
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  useEffect(() => {
    if (!data) return;

    const ws = new WebSocket(WS_URL);

    ws.onopen = () => {
      console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
      const newLog = JSON.parse(event.data);
      
      setData(currentData => {
        const updatedData = JSON.parse(JSON.stringify(currentData));
        
        updatedData.total_requests += 1;
        if (newLog.status_code < 400) {
          updatedData.successful_requests += 1;
        } else {
          updatedData.total_errors += 1;
        }

        if (newLog.status_code >= 500) {
          updatedData.status_code_counts['5xx'] += 1;
        } else if (newLog.status_code >= 400) {
          updatedData.status_code_counts['4xx'] += 1;
        } else {
          updatedData.status_code_counts['2xx'] += 1;
        }

        if (newLog.status_code >= 400) {
          const newError = {
            id: newLog.timestamp_utc, // Use timestamp for a unique key
            ...newLog
          };
          updatedData.recent_errors.unshift(newError);
          if (updatedData.recent_errors.length > 10) {
            updatedData.recent_errors.pop();
          }
        }
        
        return updatedData;
      });
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
    };

    return () => {
      ws.close();
    };

  }, [data]);

  if (loading && !data) return <div className="loading">Loading Dashboard...</div>;
  if (error) return <div className="error">Error loading data: {error}</div>;
  if (!data) return <div className="loading">No data available.</div>;

  const successRate = data.total_requests > 0 ? (data.successful_requests / data.total_requests) * 100 : 0;

  const statusPieData = [
    { name: 'Success (2xx)', value: data.status_code_counts['2xx'] || 0 },
    { name: 'Client Error (4xx)', value: data.status_code_counts['4xx'] || 0 },
    { name: 'Server Error (5xx)', value: data.status_code_counts['5xx'] || 0 },
  ];
  
  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>Rexus</h1>
        <p>Analytics Dashboard</p>
      </header>

      <div className="kpi-grid">
        <div className="kpi-card">
          <h2>Total Requests</h2>
          <p>{data.total_requests.toLocaleString()}</p>
        </div>
        <div className="kpi-card">
          <h2>Success Rate</h2>
          <p className={successRate < 80 ? 'low' : 'high'}>{successRate.toFixed(2)}%</p>
        </div>
        <div className="kpi-card">
          <h2>Total Errors</h2>
          <p>{data.total_errors.toLocaleString()}</p>
        </div>
      </div>

      <div className="main-content">
        <div className="chart-container large">
          <h3>Requests Over Time (Last 24 Hours)</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={data.requests_over_time}>
              <CartesianGrid strokeDasharray="3 3" stroke="#444" />
              <XAxis dataKey="hour" stroke="#888" />
              <YAxis stroke="#888" />
              <Tooltip contentStyle={{ backgroundColor: '#222', border: '1px solid #444' }} />
              <Legend />
              <Line type="monotone" dataKey="count" stroke="#8884d8" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-container small">
          <h3>Status Codes</h3>
           <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie data={statusPieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={100} label>
                <Cell key="success" fill={COLORS.success} />
                <Cell key="clientError" fill={COLORS.clientError} />
                <Cell key="serverError" fill={COLORS.serverError} />
              </Pie>
              <Tooltip contentStyle={{ backgroundColor: '#222', border: '1px solid #444' }} />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="table-grid">
        <div className="table-container">
          <h3>Top Endpoints</h3>
          <table>
            <thead>
              <tr><th>Path</th><th>Requests</th></tr>
            </thead>
            <tbody>
              {data.top_endpoints.map(ep => (
                <tr key={ep.request_path}><td>{ep.request_path}</td><td>{ep.count.toLocaleString()}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="table-container">
          <h3>Top Users</h3>
          <table>
            <thead>
              <tr><th>User ID</th><th>Requests</th></tr>
            </thead>
            <tbody>
              {data.top_users.map(user => (
                <tr key={user.user_id}><td>{user.user_id}</td><td>{user.count.toLocaleString()}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="table-container">
          <h3>Recent Errors</h3>
          <table>
            <thead>
              <tr><th>Timestamp</th><th>Path</th><th>Status</th></tr>
            </thead>
            <tbody>
              {data.recent_errors.map(err => (
                <tr key={err.id}>
                  <td>{new Date(err.timestamp_utc).toLocaleTimeString()}</td>
                  <td>{err.request_path}</td>
                  <td><span className="error-badge">{err.status_code}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default App;