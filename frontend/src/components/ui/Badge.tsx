import React from 'react';

interface BadgeProps {
  status: 'pass' | 'warning' | 'fail' | 'info' | 'success';
  children: React.ReactNode;
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({ status, children, className = '' }) => {
  const getStatusClass = (s: string) => {
    if (s === 'pass') return 'success';
    return s;
  };

  return (
    <span className={`status-badge ${getStatusClass(status)} ${className}`}>
      {children}
    </span>
  );
};
