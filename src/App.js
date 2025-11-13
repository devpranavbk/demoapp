
import React, { useState, useEffect } from 'react';
import './App.css';

const API_BASE = '';
const endpoints = [
  { label: 'Root', path: '/api' },
  { label: 'Hello', path: '/api/hello' },
  { label: 'Data', path: '/api/data' },
  { label: 'Compute', path: '/api/compute' },
  { label: 'Items', path: '/api/items' },
];

function App() {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);


  // Call all APIs on page load
  useEffect(() => {
    const fetchAll = async () => {
      setLoading(true);
      const newResults = [];
      for (const ep of endpoints) {
        try {
          const res = await fetch(API_BASE + ep.path);
          const data = await res.json();
          newResults.push({ label: ep.label, path: ep.path, data });
        } catch (err) {
          newResults.push({ label: ep.label, path: ep.path, data: 'Error: ' + err });
        }
      }
      setResults(newResults);
      setLoading(false);
    };
    fetchAll();
  }, []);

  const callApi = async (path) => {
    setLoading(true);
    try {
      const res = await fetch(API_BASE + path);
      const data = await res.json();
      setResults([{ label: path, path, data }]);
    } catch (err) {
      setResults([{ label: path, path, data: 'Error: ' + err }]);
    }
    setLoading(false);
  };

  return (
    <div className="app-container">
      <h1>Simple FastAPI UI</h1>
      <div className="button-group">
        {endpoints.map((ep) => (
          <button
            key={ep.path}
            onClick={() => callApi(ep.path)}
            disabled={loading}
          >
            {ep.label}
          </button>
        ))}
      </div>
      {loading ? (
        <pre>Loading...</pre>
      ) : (
        results.map((res) => (
          <div key={res.path} style={{ marginBottom: '1.2rem' }}>
            <strong>{res.label} ({res.path}):</strong>
            <pre>{typeof res.data === 'string' ? res.data : JSON.stringify(res.data, null, 2)}</pre>
          </div>
        ))
      )}
    </div>
  );
}

export default App;
