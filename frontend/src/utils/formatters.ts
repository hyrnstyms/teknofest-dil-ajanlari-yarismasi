export function maskPII(value: string | null | undefined, type: string, isMasked: boolean = true): string {
  if (!value) return "";
  if (!isMasked) return value;
  
  if (type === "national_id" && value.length === 11) {
    return value.substring(0, 3) + "******" + value.substring(9);
  }
  
  if (type === "phone" && value.length >= 10) {
    const clean = value.replace(/\s+/g, '');
    if (clean.length === 10) {
      return "0" + clean.substring(0, 3) + " *** ** " + clean.substring(8);
    }
    if (clean.length === 11 && clean.startsWith("0")) {
      return clean.substring(0, 4) + " *** ** " + clean.substring(9);
    }
    return value.substring(0, Math.floor(value.length / 3)) + "***";
  }
  
  if (type === "email" && value.includes("@")) {
    const [user, domain] = value.split("@");
    if (user.length > 2) {
      return user.substring(0, 1) + "*****@" + domain;
    }
    return "*****@" + domain;
  }
  
  return value;
}

export function formatMs(ms: number | undefined): string {
  if (ms === undefined) return "-";
  if (ms < 1000) return `${ms} ms`;
  return `${(ms / 1000).toFixed(2)} sn`;
}
