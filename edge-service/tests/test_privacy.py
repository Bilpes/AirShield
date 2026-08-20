from app.privacy import PrivacyEngine


def test_contextual_application_values_are_masked_locally():
    engine = PrivacyEngine()
    text = "Customer jack, account 123456789, called from +91 123456789 and email jack@example.com."

    protected, entities = engine.protect(text, {})

    assert protected == (
        "Customer [PERSON_1], account [CARD_OR_ACCOUNT_1], called from [PHONE_1] and email [EMAIL_1]."
    )
    assert [item["type"] for item in entities] == [
        "PERSON",
        "CARD_OR_ACCOUNT",
        "PHONE",
        "EMAIL",
    ]
    assert all(value not in protected for value in ("jack", "123456789", "+91 123456789", "jack@example.com"))
