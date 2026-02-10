import React from 'react';
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Legend,
  Tooltip,
} from 'recharts';

const GraphiquesPriorite = ({ data }) => {
  const COLORS = {
    1: '#95a5a6', // Basse
    2: '#3498db', // Moyenne
    3: '#f39c12', // Haute
    4: '#e74c3c', // Urgente
  };

  const LABELS = {
    1: 'Basse',
    2: 'Moyenne',
    3: 'Haute',
    4: 'Urgente',
  };

  const chartData = data.map(item => ({
    name: LABELS[item.priorite],
    value: item.count,
    priorite: item.priorite,
  }));

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      return (
        <div style={{
          backgroundColor: 'white',
          padding: '10px',
          border: '1px solid #ccc',
          borderRadius: '4px',
        }}>
          <p style={{ margin: 0, fontWeight: 'bold' }}>
            {payload[0].name}
          </p>
          <p style={{ margin: 0, color: payload[0].payload.fill }}>
            {payload[0].value} tâche{payload[0].value > 1 ? 's' : ''}
          </p>
        </div>
      );
    }
    return null;
  };

  if (chartData.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '40px', color: '#999' }}>
        Aucune donnée disponible
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <PieChart>
        <Pie
          data={chartData}
          cx="50%"
          cy="50%"
          labelLine={false}
          label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
          outerRadius={80}
          fill="#8884d8"
          dataKey="value"
        >
          {chartData.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={COLORS[entry.priorite]} />
          ))}
        </Pie>
        <Tooltip content={<CustomTooltip />} />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  );
};

export default GraphiquesPriorite;