from typing import Any

from backend.app.ingestion.document import Document

from backend.app.synthetic.field_generator import (
    FieldGenerator,
)

from backend.app.synthetic.pools import (
    random_person,
)

from backend.app.synthetic.scenario_mutator import (
    apply_scenario,
)

from backend.app.synthetic.document_renderer import (
    render_petition,
)


class SyntheticGenerator:

    def __init__(self):
        self.field_generator = (
            FieldGenerator()
        )

    def generate(
        self,
        source_document: dict[str, Any],
        scenario: str,
        index: int,
    ) -> Document:

        generated = (
            self.field_generator.generate(
                source_document
            )
        )

        person = random_person()

        base_fields = {
            "document_type": (
                generated.document_type
            ),
            "institution": (
                generated.institution
            ),
            "subject": (
                generated.subject
            ),
            "request_text": (
                generated.request_text
            ),
            "secondary_request_text": (
                generated.secondary_request_text
            ),

            "name": person["name"],
            "signature_name": None,

            "address": person["address"],
            "phone": person["phone"],
            "email": person["email"],
            "date": person["date"],

            "signature": person["name"],
        }

        mutated_fields, evaluation = (
            apply_scenario(
                fields=base_fields,
                scenario=scenario,
            )
        )

        text = render_petition(
            mutated_fields
        )

        self._validate_rendered_document(
            fields=mutated_fields,
            evaluation=evaluation,
        )

        return Document(
            id=f"synthetic_{index:05d}",
            source=(
                "synthetic:qwen2.5:3b-instruct"
            ),
            source_type="synthetic",
            file_type="synthetic",
            title=generated.subject,
            text=text,
            metadata={
                "synthetic": True,
                "generator_version": "v3",
                "generator_model": (
                    "qwen2.5:3b-instruct"
                ),
                "based_on_source": (
                    source_document.get(
                        "source"
                    )
                ),
                "document_type": (
                    generated.document_type
                ),
                "institution": (
                    mutated_fields[
                        "institution"
                    ]
                ),
                "scenario": scenario,
                "rag_eligible": False,
            },
            evaluation=evaluation,
        )

    @staticmethod
    def _validate_rendered_document(
        fields: dict,
        evaluation: dict,
    ) -> None:

        missing = evaluation.get(
            "expected_missing_fields",
            [],
        )

        if "adres" in missing:
            if fields.get("address"):
                raise ValueError(
                    "Adres eksik olması gerekirken dolu."
                )

        if "tarih" in missing:
            if fields.get("date"):
                raise ValueError(
                    "Tarih eksik olması gerekirken dolu."
                )

        if "imza" in missing:
            if fields.get("signature"):
                raise ValueError(
                    "İmza eksik olması gerekirken dolu."
                )

        if not missing:
            required = [
                "name",
                "address",
                "phone",
                "email",
                "date",
                "signature",
            ]

            for field in required:
                if not fields.get(field):
                    raise ValueError(
                        f"Eksiksiz belgede alan boş: {field}"
                    )