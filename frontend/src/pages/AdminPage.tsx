import React, { useEffect, useState } from 'react';
import { 
  BarChart3, 
  Clock, 
  Users, 
  FileText, 
  CheckCircle, 
  XCircle, 
  Building2 
} from 'lucide-react';
import { fetchAdminStats, AdminStats } from '../services/adminApi';

export const AdminPage: React.FC = () => {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchAdminStats()
      .then((data) => {
        setStats(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setError("İstatistikler yüklenemedi.");
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="page-container">
        <div style={{ padding: '2rem', textAlign: 'center' }}>Yükleniyor...</div>
      </div>
    );
  }

  if (error || !stats) {
    return (
      <div className="page-container">
        <div className="alert alert-danger">{error}</div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h2 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <BarChart3 size={24} />
          Yönetici Paneli
        </h2>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
        {/* Toplam Evrak */}
        <div className="card">
          <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-secondary)' }}>
              <FileText size={18} />
              <span style={{ fontSize: '0.9rem', fontWeight: 600 }}>Toplam Evrak</span>
            </div>
            <div style={{ fontSize: '2rem', fontWeight: 700 }}>{stats.total_cases}</div>
            <div style={{ fontSize: '0.85rem', color: 'var(--success-color)' }}>
              +{stats.today_cases} bugün eklendi
            </div>
          </div>
        </div>

        {/* Ortalama İşlem Süresi */}
        <div className="card">
          <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-secondary)' }}>
              <Clock size={18} />
              <span style={{ fontSize: '0.9rem', fontWeight: 600 }}>Ortalama İşlem Süresi</span>
            </div>
            <div style={{ fontSize: '2rem', fontWeight: 700 }}>{stats.average_processing_hours} <span style={{ fontSize: '1rem' }}>saat</span></div>
          </div>
        </div>

        {/* İnsan İnceleme Oranı */}
        <div className="card">
          <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-secondary)' }}>
              <Users size={18} />
              <span style={{ fontSize: '0.9rem', fontWeight: 600 }}>İnsan İnceleme (Human Review)</span>
            </div>
            <div style={{ fontSize: '2rem', fontWeight: 700 }}>
              {(stats.human_review_ratio * 100).toFixed(1)}%
            </div>
          </div>
        </div>

        {/* Taslak Onay/Red */}
        <div className="card">
          <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-secondary)' }}>
              <CheckCircle size={18} />
              <span style={{ fontSize: '0.9rem', fontWeight: 600 }}>Taslak Kararları</span>
            </div>
            <div style={{ display: 'flex', gap: '1rem', marginTop: '0.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', color: 'var(--success-color)' }}>
                <CheckCircle size={16} /> <strong>{stats.draft_metrics.approved}</strong> onay
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', color: 'var(--danger-color)' }}>
                <XCircle size={16} /> <strong>{stats.draft_metrics.rejected}</strong> red/rev.
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <Building2 size={18} />
          Kurum ve Birim Bazlı Dağılım
        </div>
        <div className="card-body" style={{ padding: 0 }}>
          {stats.department_distribution.length === 0 ? (
            <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
              Henüz evrak bulunmuyor.
            </div>
          ) : (
            <table className="table" style={{ margin: 0 }}>
              <thead>
                <tr>
                  <th>Kurum</th>
                  <th>Birim (Department Code)</th>
                  <th style={{ textAlign: 'right' }}>Evrak Sayısı</th>
                </tr>
              </thead>
              <tbody>
                {stats.department_distribution.map((item, idx) => (
                  <tr key={`${item.institution_id}-${item.department_code}-${idx}`}>
                    <td><span className="badge badge-info">{item.institution_id}</span></td>
                    <td>{item.department_code}</td>
                    <td style={{ textAlign: 'right', fontWeight: 600 }}>{item.count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
};
