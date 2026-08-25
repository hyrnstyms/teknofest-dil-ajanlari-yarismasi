import React from "react";
import { FileText } from "lucide-react";
import type { DraftInfo, OfficialWritingContext } from "../types";

interface Props {
  draft: DraftInfo;
  analysisId?: string;
}

export const DocumentPreview: React.FC<Props> = ({ draft, analysisId }) => {
  const context = getOfficialContext(draft);
  const renderedText = typeof draft?.official_rendered_text === "string" ? draft.official_rendered_text : "";

  if (!context && !renderedText) {
    return (
      <div className="document-stage">
        <div className="document-empty">
          <FileText size={38} />
          <h2>Resmî yazı henüz oluşturulmadı</h2>
          <p>Analiz tamamlandığında mevcut resmî yazı verileri burada A4 görünümünde gösterilecek.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="document-stage">
      <article id="document-print-area" className="a4-document">
        {context ? <StructuredDocument context={context} /> : <pre className="official-text-fallback">{renderedText}</pre>}
        {analysisId && <footer className="document-operation-id">İşlem ID: {analysisId}</footer>}
      </article>
    </div>
  );
};

function getOfficialContext(draft?: DraftInfo): OfficialWritingContext | null {
  if (!draft) return null;
  if (draft.mod_c_validated_context && typeof draft.mod_c_validated_context === "object") {
    return draft.mod_c_validated_context;
  }
  if (typeof draft.official_render === "object" && draft.official_render?.context) {
    return draft.official_render.context;
  }
  return null;
}

const StructuredDocument: React.FC<{ context: OfficialWritingContext }> = ({ context }) => {
  const recipient = typeof context.muhatap === "string" ? context.muhatap : context.muhatap?.isim;
  const paragraphs = Array.isArray(context.metin_paragraflari) ? context.metin_paragraflari : [];
  const attachments = Array.isArray(context.ekler) ? context.ekler : [];

  return (
    <>
      <header className="document-letterhead">
        <strong>T.C.</strong>
        {context.tc_baslik?.idare_adi && <strong>{context.tc_baslik.idare_adi.toLocaleUpperCase("tr-TR")}</strong>}
        {context.tc_baslik?.birim_adi && <span>{context.tc_baslik.birim_adi}</span>}
      </header>

      {(context.sayi || context.tarih) && (
        <div className="document-number-date">
          <span>{context.sayi && <>Sayı: {context.sayi}</>}</span>
          <span>{context.tarih}</span>
        </div>
      )}
      {context.konu && <div className="document-subject"><strong>Konu:</strong> {context.konu}</div>}
      {recipient && <h2 className="document-recipient">{context.muhatap && typeof context.muhatap !== "string" && context.muhatap.tur === "gercek_kisi" ? `Sayın ${recipient}` : recipient.toLocaleUpperCase("tr-TR")}</h2>}

      {context.ilgi?.map((item, index) => (
        <p className="document-reference" key={`${item.sayi}-${index}`}>
          <strong>İlgi:</strong> {[item.tarih && `${item.tarih} tarihli`, item.sayi && `${item.sayi} sayılı`, item.aciklama].filter(Boolean).join(" ")}.
        </p>
      ))}

      <section className="document-body">
        {paragraphs.map((paragraph, index) => <p key={index}>{paragraph}</p>)}
        {context.kapalis_ifadesi && <p>{context.kapalis_ifadesi}</p>}
      </section>

      {context.imza && (context.imza.ad_soyad || context.imza.unvan) && (
        <div className="document-signature">
          {context.imza.ad_soyad && <strong>{context.imza.ad_soyad}</strong>}
          {context.imza.unvan && <span>{context.imza.unvan}</span>}
        </div>
      )}

      {attachments.length > 0 && (
        <section className="document-list-block">
          <strong>Ek{attachments.length > 1 ? "ler" : ""}:</strong>
          {attachments.map((attachment, index) => (
            <span key={`${attachment.ad}-${index}`}>{index + 1}. {attachment.ad}{attachment.bilgi ? ` (${attachment.bilgi})` : ""}</span>
          ))}
        </section>
      )}

      {context.dagitim && ((context.dagitim.geregi?.length || 0) + (context.dagitim.bilgi?.length || 0) > 0) && (
        <section className="document-list-block">
          <strong>Dağıtım:</strong>
          {context.dagitim.geregi?.map((item) => <span key={`geregi-${item}`}>Gereği: {item}</span>)}
          {context.dagitim.bilgi?.map((item) => <span key={`bilgi-${item}`}>Bilgi: {item}</span>)}
        </section>
      )}

      {context.iletisim && (context.iletisim.adres || context.iletisim.irtibat || context.iletisim.telefon) && (
        <div className="document-contact">
          {[context.iletisim.adres, context.iletisim.irtibat, context.iletisim.telefon].filter(Boolean).join(" | ")}
        </div>
      )}
    </>
  );
};
