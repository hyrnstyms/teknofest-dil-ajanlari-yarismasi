export interface AdminStats {
  total_cases: number;
  today_cases: number;
  average_processing_hours: number;
  human_review_ratio: number;
  department_distribution: {
    institution_id: string;
    department_code: string;
    count: number;
  }[];
  draft_metrics: {
    approved: number;
    rejected: number;
  };
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function fetchAdminStats(institutionId?: string): Promise<AdminStats> {
  let url = `${API_BASE_URL}/api/admin/stats`;
  if (institutionId) {
    url += `?institution_id=${encodeURIComponent(institutionId)}`;
  }
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error("Stats fetch failed");
  }
  return res.json();
}
