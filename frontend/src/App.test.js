import { render, screen } from '@testing-library/react';
import App from './App';

test('renders AFOC heading', () => {
  render(<App />);
  const headingElement = screen.getByText(/AFOC/i);
  expect(headingElement).toBeInTheDocument();
});
