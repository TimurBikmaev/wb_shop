import pytest


@pytest.fixture
def email_sender(monkeypatch):
    sent_emails = []

    def fake_send_mail(
        subject,
        message,
        from_email,
        recipient_list,
        **kwargs,
    ):
        sent_emails.append({
            'subject': subject,
            'message': message,
            'recipient_list': recipient_list,
        })

    monkeypatch.setattr(
        'user.services.send_mail',
        fake_send_mail,
    )

    return sent_emails
