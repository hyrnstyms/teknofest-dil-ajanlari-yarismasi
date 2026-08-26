import React from "react";

type EVRAGBrandProps = {
  variant?: "full" | "compact" | "icon";
  theme?: "light" | "dark";
  className?: string;
};

export const EVRAGBrand: React.FC<EVRAGBrandProps> = ({
  variant = "full",
  theme = "dark",
  className = "",
}) => (
  <div className={`evrag-brand evrag-brand-${variant} evrag-brand-${theme} ${className}`.trim()}>
    <img src="/brand/evrag-logo.png" alt="EVRAG" />
    {variant === "full" ? <span>Akıllı Evrak Yönetimi</span> : null}
  </div>
);