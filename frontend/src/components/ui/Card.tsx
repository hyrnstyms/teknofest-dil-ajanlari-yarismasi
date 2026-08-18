import React from 'react';

interface CardProps {
  children: React.ReactNode;
  title?: React.ReactNode;
  icon?: React.ReactNode;
  className?: string;
}

export const Card: React.FC<CardProps> = ({ children, title, icon, className = '' }) => {
  return (
    <div className={`card ${className}`}>
      {(title || icon) && (
        <div className="card-header border-b border-border-light pb-4 mb-4 flex items-center gap-2">
          {icon && <span className="text-muted">{icon}</span>}
          {title && <h3 className="card-title text-lg font-bold text-text-heading m-0">{title}</h3>}
        </div>
      )}
      <div>{children}</div>
    </div>
  );
};
