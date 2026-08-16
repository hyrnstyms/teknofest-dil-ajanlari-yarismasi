def render_petition(
    fields: dict,
) -> str:

    lines = []

    if fields.get("date"):
        lines.append(
            fields["date"]
        )

    lines.append("")
    lines.append(
        fields["institution"].upper()
    )
    lines.append("")

    lines.append(
        f"Konu: {fields['subject']}"
    )

    lines.append("")

    lines.append(
        fields["request_text"]
    )

    lines.append("")
    lines.append(
        "Gereğini arz ederim."
    )

    lines.append("")

    lines.append(
        f"Ad Soyad: {fields['name']}"
    )

    lines.append(
        f"Adres: {fields.get('address', '')}"
    )

    lines.append(
        f"Telefon: {fields.get('phone', '')}"
    )

    lines.append(
        f"E-posta: {fields.get('email', '')}"
    )

    lines.append(
        f"İmza: {fields.get('signature', '')}"
    )

    # Çelişkili bilgi senaryosunda
    # imza sahibinin adı farklı olabilir.
    signature_name = fields.get(
        "signature_name"
    )

    if signature_name:
        lines.append(
            f"İmzalayan: {signature_name}"
        )

    return "\n".join(lines).strip()