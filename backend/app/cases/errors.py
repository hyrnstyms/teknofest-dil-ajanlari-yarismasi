"""Case-domain errors mapped to the frozen API error envelope."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException


class CaseError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.context = context or {}

    def to_http_exception(self) -> HTTPException:
        return HTTPException(
            status_code=self.status_code,
            detail={
                "code": self.code,
                "message": self.message,
                "context": self.context,
            },
        )


def authentication_required() -> CaseError:
    return CaseError(
        401,
        "authentication_required",
        "Bu işlem için kimlik doğrulama gereklidir.",
    )


def invalid_token() -> CaseError:
    return CaseError(401, "invalid_token", "Kimlik bilgisi geçersiz veya süresi dolmuş.")


def case_not_found() -> CaseError:
    return CaseError(404, "case_not_found", "Dosya bulunamadı.")


def action_forbidden(message: str | None = None, **context: Any) -> CaseError:
    return CaseError(
        403,
        "action_forbidden",
        message or "Bu işlem için yetkiniz bulunmamaktadır.",
        context,
    )


def invalid_department(code: str) -> CaseError:
    return CaseError(
        400,
        "invalid_department",
        "Hedef birim kurum profilinde tanımlı değil.",
        {"department_code": code},
    )


def invalid_case_transition(current_status: str, target_status: str | None = None) -> CaseError:
    context: dict[str, Any] = {"current_status": current_status}
    if target_status:
        context["target_status"] = target_status
    return CaseError(
        409,
        "invalid_case_transition",
        "İşlem mevcut dosya durumunda gerçekleştirilemez.",
        context,
    )


def confirmation_required() -> CaseError:
    return CaseError(
        409,
        "confirmation_required",
        "Bu işlem açık onay gerektirir. confirmed=true gönderilmelidir.",
    )


def version_conflict(expected: int, actual: int) -> CaseError:
    return CaseError(
        409,
        "version_conflict",
        "Dosya başka bir işlemle güncellenmiş. Sayfayı yenileyip tekrar deneyin.",
        {"expected": expected, "actual": actual},
    )


def validation_error(message: str, **context: Any) -> CaseError:
    return CaseError(400, "validation_error", message, context)


def verified_department_action_required() -> CaseError:
    return CaseError(
        409,
        "verified_department_action_required",
        "Resmi yanıt için doğrulanmış birim işlemi gereklidir.",
    )


def approved_draft_required() -> CaseError:
    return CaseError(
        409,
        "approved_draft_required",
        "Dosya tamamlamak için onaylı taslak gereklidir.",
    )


def citizen_token_invalid() -> CaseError:
    return CaseError(
        404,
        "citizen_token_invalid",
        "Takip kodu veya erişim anahtarı geçersiz.",
    )


def clarification_not_active() -> CaseError:
    return CaseError(
        409,
        "clarification_not_active",
        "Aktif bir ek bilgi talebi bulunmamaktadır.",
    )
