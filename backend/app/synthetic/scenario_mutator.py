from copy import deepcopy

from backend.app.synthetic.pools import (
    different_name,
    wrong_institution,
)


def apply_scenario(
    fields: dict,
    scenario: str,
) -> tuple[dict, dict]:

    result = deepcopy(fields)

    evaluation = {
        "scenario": scenario,
        "expected_missing_fields": [],
        "requires_additional_information": False,
        "requires_route_correction": False,
        "requires_style_revision": False,
        "contains_multiple_requests": False,
        "contains_conflicting_information": False,
        "expected_route": None,
        "label_status": "synthetic_programmatic_v3",
    }

    if scenario == "eksiksiz_basvuru":
        return result, evaluation

    if scenario == "eksik_adres":

        result["address"] = ""

        evaluation[
            "expected_missing_fields"
        ] = ["adres"]

        evaluation[
            "requires_additional_information"
        ] = True

        return result, evaluation

    if scenario == "eksik_tarih":

        result["date"] = ""

        evaluation[
            "expected_missing_fields"
        ] = ["tarih"]

        evaluation[
            "requires_additional_information"
        ] = True

        return result, evaluation

    if scenario == "eksik_imza":

        result["signature"] = ""

        evaluation[
            "expected_missing_fields"
        ] = ["imza"]

        evaluation[
            "requires_additional_information"
        ] = True

        return result, evaluation

    if scenario == "belirsiz_talep":

        result["request_text"] = (
            "Kurumunuzla ilgili yaşadığım durum hakkında "
            "gerekli işlemlerin yapılmasını talep ediyorum."
        )

        evaluation[
            "expected_missing_fields"
        ] = ["talep_aciklamasi"]

        evaluation[
            "requires_additional_information"
        ] = True

        return result, evaluation

    if scenario == "yanlis_kuruma_yonlendirme":

        correct = result[
            "institution"
        ]

        result["institution"] = (
            wrong_institution(correct)
        )

        evaluation[
            "requires_route_correction"
        ] = True

        evaluation[
            "expected_route"
        ] = correct

        return result, evaluation

    if scenario == "birden_fazla_talep":

        result["request_text"] = (
            result["request_text"]
            + "\n\nAyrıca, "
            + result["secondary_request_text"]
        )

        evaluation[
            "contains_multiple_requests"
        ] = True

        return result, evaluation

    if scenario == "celiskili_bilgi":

        result["signature_name"] = (
            different_name(
                result["name"]
            )
        )

        evaluation[
            "contains_conflicting_information"
        ] = True

        evaluation[
            "requires_additional_information"
        ] = True

        evaluation[
            "conflicting_fields"
        ] = ["ad_soyad"]

        return result, evaluation

    if scenario == "resmi_uslubu_zayif_basvuru":

        result["request_text"] = (
            f"Merhaba, {result['subject'].lower()} "
            "konusundaki işimin bir an önce "
            "halledilmesini istiyorum. "
            "Bu meseleyle ilgilenip hızlıca "
            "çözerseniz sevinirim."
        )

        evaluation[
            "requires_style_revision"
        ] = True

        return result, evaluation

    raise ValueError(
        f"Bilinmeyen senaryo: {scenario}"
    )