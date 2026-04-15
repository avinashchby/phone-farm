from phone_farm.qa_agent.login_detect import detect_login_screen, extract_login_fields

LOGIN_XML = """<?xml version="1.0"?>
<hierarchy>
  <android.widget.FrameLayout>
    <android.widget.EditText resource-id="com.app:id/email_field"
      text="" content-desc="Email" inputType="textEmailAddress" />
    <android.widget.EditText resource-id="com.app:id/password_field"
      text="" content-desc="Password" inputType="textPassword" />
    <android.widget.Button resource-id="com.app:id/sign_in_btn"
      text="Sign in" clickable="true" />
  </android.widget.FrameLayout>
</hierarchy>"""

OAUTH_XML = """<?xml version="1.0"?>
<hierarchy>
  <android.widget.FrameLayout>
    <android.widget.Button text="Continue with Google" clickable="true" />
  </android.widget.FrameLayout>
</hierarchy>"""

HOME_XML = """<?xml version="1.0"?>
<hierarchy>
  <android.widget.FrameLayout>
    <android.widget.TextView text="Welcome back!" />
    <android.widget.Button text="Settings" clickable="true" />
  </android.widget.FrameLayout>
</hierarchy>"""


def test_detects_password_field():
    assert detect_login_screen(LOGIN_XML) is True


def test_detects_oauth_button():
    assert detect_login_screen(OAUTH_XML) is True


def test_home_screen_not_login():
    assert detect_login_screen(HOME_XML) is False


def test_extracts_email_field():
    fields = extract_login_fields(LOGIN_XML)
    assert "email" in fields["email_field"]


def test_extracts_password_field():
    fields = extract_login_fields(LOGIN_XML)
    assert "password" in fields["password_field"]


def test_extracts_submit_button():
    fields = extract_login_fields(LOGIN_XML)
    assert "sign_in_btn" in fields["submit_button"]


def test_invalid_xml_returns_false():
    assert detect_login_screen("not xml") is False


def test_extract_fields_invalid_xml_returns_nulls():
    fields = extract_login_fields("not xml")
    assert fields == {"email_field": None, "password_field": None, "submit_button": None}
