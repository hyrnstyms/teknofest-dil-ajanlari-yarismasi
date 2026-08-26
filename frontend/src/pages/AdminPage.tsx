import React from 'react';
import { Clock } from 'lucide-react';

export const AdminPage: React.FC = () => {
  return (
    <div className="page-container">
      <div className="card">
        <div className="card-header">
          <Clock size={18} /> Yönetici Paneli
        </div>
        <div className="card-body" style={{ textAlign: 'center', padding: '3rem' }}>
          <p className="text-secondary" style={{ fontSize: '1.1rem' }}>
            Bu panel, Kişi 1'in backend parçası (<code>GET /api/admin/stats</code>) hazır olduğunda aktif olacaktır.
          </p>
          <div className="badge badge-warning" style={{ marginTop: '1rem', fontSize: '0.9rem' }}>
            Görev 4 — Bekliyor
          </div>
        </div>
      </div>
    </div>
  );
};
