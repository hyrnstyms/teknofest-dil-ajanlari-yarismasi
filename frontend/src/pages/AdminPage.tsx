import React from 'react';
import { useNavigate } from 'react-router-dom';
import { AdminDashboard } from '../components/AdminDashboard';

export const AdminPage: React.FC = () => {
  const navigate = useNavigate();
  return (
    <div className="page-container">
      <AdminDashboard onOpenAnalysis={(analysisId) => navigate(`/evrak/${analysisId}`)} />
    </div>
  );
};
