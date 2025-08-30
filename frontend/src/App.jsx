import { useState, useEffect, useRef } from 'react';
import './App.css';

const API_BASE_URL = 'http://localhost:8000';
const WS_BASE_URL = 'ws://localhost:8000';

function App() {
  const [isConnected, setIsConnected] = useState(false);
  const [analytics, setAnalytics] = useState(null);
  const [logs, setLogs] = useState([]);
  const websocket = useRef(null);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/analytics`);
        if (!response.ok) throw new Error('Network response was not ok');
        const data = await response.json();
        setAnalytics(data);
      } catch (error) {
        console.error("Failed to fetch analytics:", error);
      }
    };
    fetchAnalytics();
  }, []);

  useEffect(() => {
    const connect = () => {
      websocket.current = new WebSocket(`${WS_BASE_URL}/ws/logs`);

      websocket.current.onopen = () => {
        console.log("WebSocket Connected");
        setIsConnected(true);
      };

      websocket.current.onclose = () => {
        console.log("WebSocket Disconnected");
        setIsConnected(false);
        setTimeout(connect, 3000);
      };

      websocket.current.onmessage = (event) => {
        const newLog = JSON.parse(event.data);
        setLogs(prevLogs => [{ ...newLog, id: Date.now() }, ...prevLogs.slice(0, 100)]);
      };

      websocket.current.onerror = (error) => {
        console.error("WebSocket Error:", error);
        websocket.current.close();
      };
    };

    connect();

    return () => {
      if (websocket.current) {
        websocket.current.close();
      }
    };
  }, []);

  return (
    <div className="dashboard-container">
      <header>
        <h1>API Fortress Dashboard</h1>
        <div className="status-indicator">
          <div className={`dot ${isConnected ? 'connected' : ''}`}></div>
          <span>{isConnected ? 'Live' : 'Disconnected'}</span>
        </div>
      </header>

      <section className="kpi-grid">
        <KpiCard title="Total Requests (24h)" value={analytics?.total_requests ?? '...'} />
        <KpiCard title="Success Rate" value={analytics?.success_rate ?? '...'} unit="%" />
        <KpiCard title="Failed Requests (24h)" value={analytics?.failed_requests ?? '...'} />
        <KpiCard title="Average Latency" value={analytics?.average_latency_ms ?? '...'} unit="ms" />
      </section>

      <section className="live-logs-container">
        <div className="logs-header">Live Request Stream</div>
        <div className="logs-stream">
          {logs.map(log => <LogEntry key={log.id} log={log} />)}
        </div>
      </section>
    </div>
  );
}

const KpiCard = ({ title, value, unit }) => (
  <div className="kpi-card">
    <h3>{title}</h3>
    <p className="value">
      {value}
      {unit && <span className="unit">{unit}</span>}
    </p>
  </div>
);

const LogEntry = ({ log }) => {
  const isSuccess = log.status_code >= 200 && log.status_code < 400;
  const latencyWidth = Math.min((log.latency_ms / 1000) * 100, 100); // Scale latency for the bar, max 1s

  return (
    <div className={`log-entry ${isSuccess ? 'success' : 'failure'}`}>
      <span className={`log-method ${log.method}`}>{log.method}</span>
      <span className="log-path">/{log.path}</span>
      <span className={`log-status ${isSuccess ? 'success' : 'failure'}`}>{log.status_code}</span>
      <div title={`${log.latency_ms}ms`}>
        <div className="log-latency-bar">
          <div className="fill" style={{ width: `${latencyWidth}%` }}></div>
        </div>
      </div>
    </div>
  );
};

export default App;