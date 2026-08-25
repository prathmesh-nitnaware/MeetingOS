import React from "react"

interface StatusBadgeProps {
  status: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  const normalizedStatus = status.toLowerCase();
  return (
    <span className={`badge badge-${normalizedStatus}`}>
      <span className="dot">●</span>
      {status}
    </span>
  );
};
export default StatusBadge
