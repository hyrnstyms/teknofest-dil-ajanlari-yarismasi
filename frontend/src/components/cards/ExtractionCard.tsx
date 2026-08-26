import React from "react";
import { List } from "lucide-react";
import { ExtractionInfo } from "../../types";

interface Props {
  extraction: ExtractionInfo;
}

export const ExtractionCard: React.FC<Props> = ({ extraction }) => {
  if (!extraction?.fields || Object.keys(extraction.fields).length === 0) {
    return (
      <div className="card mb-4">
        <div className="card-header"><List size={18}/> Önemli Bilgiler</div>
        <div className="card-body">
          <p className="text-secondary">Çıkarılan bilgi bulunamadı.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="card mb-4">
      <div className="card-header"><List size={18}/> Önemli Bilgiler</div>
      <div className="card-body p-0">
        <table className="data-table">
          <tbody>
            {Object.entries(extraction.fields).map(([key, field]) => {
              const displayValue = formatExtractionFieldValue(field);

              return (
                <tr key={key}>
                  <th>{formatKey(key)}</th>
                  <td>
                    {displayValue !== null ? (
                      <span className="font-medium">{displayValue}</span>
                    ) : (
                      <span className="text-secondary text-sm">Belirtilmemiş</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

function formatExtractionFieldValue(field: unknown): string | null {
  const rawValue =
    isRecord(field) && Object.hasOwn(field, "value")
      ? field.value
      : field;

  return formatRawValue(rawValue);
}

function formatRawValue(value: unknown): string | null {
  if (value === null || value === undefined) {
    return null;
  }

  if (typeof value === "boolean") {
    return value ? "Evet" : "Hayır";
  }

  if (typeof value === "string") {
    const trimmed = value.trim();
    return trimmed || null;
  }

  if (Array.isArray(value)) {
    const items = value
      .map(formatListItem)
      .filter((item): item is string => Boolean(item));

    return items.length > 0 ? items.join(", ") : null;
  }

  if (isRecord(value)) {
    return formatRecordValue(value);
  }

  return String(value);
}

function formatListItem(item: unknown): string | null {
  if (!isRecord(item)) {
    return formatRawValue(item);
  }

  const primaryValue =
    item.name
    ?? item.value
    ?? item.text
    ?? item.label
    ?? item.evidence;
  const formattedValue = formatRawValue(primaryValue);

  if (!formattedValue) {
    return formatRecordValue(item);
  }

  const type = typeof item.type === "string" ? item.type.trim() : "";
  return type ? `${type}: ${formattedValue}` : formattedValue;
}

function formatRecordValue(value: Record<string, unknown>): string | null {
  const parts = Object.entries(value)
    .map(([key, item]) => {
      const formattedItem = formatRawValue(item);
      return formattedItem ? `${formatKey(key)}: ${formattedItem}` : null;
    })
    .filter((item): item is string => Boolean(item));

  return parts.length > 0 ? parts.join(", ") : null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function formatKey(key: string): string {
  return key
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}
