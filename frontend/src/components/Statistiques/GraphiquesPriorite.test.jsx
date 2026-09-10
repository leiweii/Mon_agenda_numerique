import React from 'react';
import { render, screen } from '@testing-library/react';
import GraphiquesPriorite from './GraphiquesPriorite';

jest.mock('recharts', () => ({
  ResponsiveContainer: ({ children }) => <div>{children}</div>,
  PieChart: ({ children }) => <div>{children}</div>,
  Pie: ({ data, label, children }) => (
    <div>
      {data.map((entry) => <span key={entry.priorite}>{label({ name: entry.name, percent: 0.5 })}</span>)}
      {children}
    </div>
  ),
  Cell: () => null,
  Legend: () => null,
  Tooltip: () => null,
}));

test('renders the four normalized priority entries in the chart', () => {
  render(
    <GraphiquesPriorite
      data={[
        { priorite: 1, count: 1 },
        { priorite: 2, count: 0 },
        { priorite: 3, count: 2 },
        { priorite: 4, count: 0 },
      ]}
    />
  );

  expect(screen.getByText('Basse 50%')).toBeInTheDocument();
  expect(screen.getByText('Moyenne 50%')).toBeInTheDocument();
  expect(screen.getByText('Haute 50%')).toBeInTheDocument();
  expect(screen.getByText('Urgente 50%')).toBeInTheDocument();
});

test('renders an empty state when there is no priority data', () => {
  render(<GraphiquesPriorite data={[]} />);

  expect(screen.getByText('Aucune donnée disponible')).toBeInTheDocument();
});
