import React from "react"

interface SpinnerProps {
  message?: string;
}

export const Spinner: React.FC<SpinnerProps> = ({ message = "Loading data..." }) => {
  return (
    <div className="loading-container" data-testid="loading-spinner">
      <div className="spinner"></div>
      <span>{message}</span>
    </div>
  );
};
export default Spinner
