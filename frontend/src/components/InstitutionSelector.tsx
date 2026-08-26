import React, { useEffect, useState } from "react";
import { Building2 } from "lucide-react";

import { api, type InstitutionOption } from "../services/api";

interface InstitutionSelectorProps {
  value: string;
  onChange: (institution: InstitutionOption | null) => void;
  disabled: boolean;
  compact?: boolean;
  topbar?: boolean;
}

export const InstitutionSelector: React.FC<InstitutionSelectorProps> = ({
  value,
  onChange,
  disabled,
  compact = false,
  topbar = false,
}) => {
  const [options, setOptions] = useState<InstitutionOption[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const selectedInstitution = options.find(
    (institution) => institution.id === value,
  );

  useEffect(() => {
    let isMounted = true;

    api.listInstitutionOptions()
      .then((institutions) => {
        if (isMounted) {
          setOptions(institutions);
        }
      })
      .catch(() => {
        if (isMounted) {
          setLoadError("Kurum listesi yüklenemedi.");
        }
      })
      .finally(() => {
        if (isMounted) {
          setIsLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <div className={topbar ? "institution-selector topbar-selector" : compact ? "institution-selector compact" : "card mb-6 institution-selector"}>
      {!topbar && <div className={compact ? "institution-selector-title" : "card-header"}>
        <Building2 size={20} className="text-primary" />
        Kurum Seçimi
      </div>}
      <div className={topbar || compact ? "institution-selector-body" : "card-body"}>
        {!topbar && <label htmlFor="institution-selector" className="font-medium">Analizin yapılacağı kurum</label>}
        <select
          id="institution-selector"
          value={value}
          onChange={(event) => {
            const selected = options.find(
              (institution) => institution.id === event.target.value,
            );
            onChange(selected ?? null);
          }}
          disabled={disabled || isLoading || Boolean(loadError)}
          required
          aria-label={topbar ? "Seçili kurum" : undefined}
          style={{ width: "100%", marginTop: topbar ? 0 : "0.5rem" }}
        >
          <option value="">
            {isLoading ? "Kurumlar yükleniyor..." : "Kurum seçin"}
          </option>
          {options.map((institution) => (
            <option key={institution.id} value={institution.id}>
              {institution.label}
            </option>
          ))}
        </select>
        {selectedInstitution && !compact && !topbar && (
          <div className="mt-4">
            <p className="font-medium">
              {selectedInstitution.ui_config.title ?? selectedInstitution.label}
            </p>
            {selectedInstitution.ui_config.description && (
              <p className="text-sm text-secondary mt-2">
                {selectedInstitution.ui_config.description}
              </p>
            )}
          </div>
        )}
        {loadError && (
          <p className="text-sm text-error mt-2">{loadError}</p>
        )}
      </div>
    </div>
  );
};
