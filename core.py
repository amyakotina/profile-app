"""
    Методы возвращают пару (data, error):
  - при успехе:  (data, None)
  - при ошибке:  (None, (message, http_status))
Веб-слой (app.py) превращает это в JSON-ответы и HTML-страницы.
"""

import re
import random
import secrets

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
REQUIRED_QUESTIONNAIRE = ("first_name", "last_name", "age", "city")


class AuthService:
    def __init__(self):
        self.users = {}    # email -> user dict
        self.codes = {}    # email -> последний код
        self.tokens = {}   # token -> email

    # ---------- вспомогательное ----------
    def _get_or_create_user(self, email):
        return self.users.setdefault(email, {
            "email": email,
            "verified": False,
            "profile_completed": False,
            "profile": None,
        })

    def user_by_token(self, token):
        email = self.tokens.get(token or "")
        return self.users.get(email) if email else None

    # ---------- авторизация ----------
    def request_code(self, email):
        if not EMAIL_RE.match(email or ""):
            return None, ("Некорректный email", 400)
        self._get_or_create_user(email)
        code = f"{random.randint(0, 999999):06d}"
        self.codes[email] = code
        return {"email": email, "code": code}, None

    def verify_code(self, email, code):
        if not email or self.codes.get(email) != str(code):
            return None, ("Неверный код или email", 400)
        user = self._get_or_create_user(email)
        user["verified"] = True
        token = secrets.token_hex(16)
        self.tokens[token] = email
        self.codes.pop(email, None)
        return {"token": token, "profile_completed": user["profile_completed"]}, None

    # ---------- анкета и профиль ----------
    def submit_questionnaire(self, token, data):
        user = self.user_by_token(token)
        if not user:
            return None, ("Не авторизован", 401)
        for field in REQUIRED_QUESTIONNAIRE:
            if not str(data.get(field, "")).strip():
                return None, (f"Поле '{field}' обязательно", 400)
        age, err = _parse_age(data.get("age"))
        if err:
            return None, (err, 400)
        user["profile"] = {
            "email": user["email"],
            "first_name": str(data["first_name"]).strip(),
            "last_name": str(data["last_name"]).strip(),
            "age": age,
            "city": str(data["city"]).strip(),
            "bio": str(data.get("bio", "")).strip(),
        }
        user["profile_completed"] = True
        return user["profile"], None

    def get_profile(self, token):
        user = self.user_by_token(token)
        if not user:
            return None, ("Не авторизован", 401)
        if not user["profile_completed"]:
            return None, ("Сначала заполните анкету", 403)
        return user["profile"], None

    def update_profile(self, token, data):
        user = self.user_by_token(token)
        if not user:
            return None, ("Не авторизован", 401)
        if not user["profile_completed"]:
            return None, ("Сначала заполните анкету", 403)
        profile = user["profile"]
        for field in ("first_name", "last_name", "city", "bio"):
            if field in data and str(data[field]).strip():
                profile[field] = str(data[field]).strip()
        if data.get("age") not in (None, ""):
            age, err = _parse_age(data.get("age"))
            if err:
                return None, (err, 400)
            profile["age"] = age
        return profile, None


def _parse_age(value):
    try:
        age = int(value)
    except (TypeError, ValueError):
        return None, "Возраст должен быть числом"
    if not 0 < age < 120:
        return None, "Возраст должен быть в диапазоне 1–119"
    return age, None
