import React from 'react';
import { User, ShieldCheck } from 'lucide-react';

interface TopbarProps {
  currentPath: string;
}

export function Topbar({ currentPath }: TopbarProps) {
  const getPageInfo = () => {
    switch(currentPath) {
      case 'new': return { title: 'Yeni Evrak', subtitle: 'Sisteme yeni evrak yükleyin veya metin girin' };
      case 'analysis': return { title: 'Evrak Analizi', subtitle: 'Yapay zeka destekli detaylı evrak analizi ve karar destek sonuçları' };
      case 'documents': return { title: 'Evraklar', subtitle: 'Sistemdeki tüm evrakların listesi' };
      case 'review-queue': return { title: 'İnceleme Kuyruğu', subtitle: 'Personel onayı veya incelemesi bekleyen işlemler' };
      case 'performance': return { title: 'Sistem Performansı', subtitle: 'İşlem süreleri, iş yükü ve otomasyon analizleri' };
      case 'status': return { title: 'Sistem Durumu', subtitle: 'Arka plan servislerinin anlık bağlantı durumu' };
      default: return { title: 'KAMUAI', subtitle: 'Karar Destek Sistemi' };
    }
  };

  const { title, subtitle } = getPageInfo();

  return (
    <header className="topbar flex justify-between items-center">
      <div className="flex-col">
        <h2 className="font-semibold text-heading">{title}</h2>
        <p className="text-sm text-muted">{subtitle}</p>
      </div>
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2 text-sm text-muted">
          <ShieldCheck size={18} className="text-success" />
          <span>Kurum: <strong>Örnek Bakanlık</strong></span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-border-color flex items-center justify-center text-primary">
            <User size={18} />
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-medium">Demo Kullanıcı</span>
            <span className="text-xs text-muted">Evrak Personeli</span>
          </div>
        </div>
      </div>
    </header>
  );
}

