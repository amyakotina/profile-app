import os

import pytest
import requests

BASE = os.environ.get("APP_BASE", "http://localhost:5001")


def test_correct_email():
    """Запрос кода на корректный e-mail"""
    email = "kkaplin64@gmail.com"
    r = requests.post(f"{BASE}/api/auth/request-code", json={"email": email})
    assert r.status_code == 200
    k = r.json()
    assert k["email"] == email
    assert "code" in k
    assert len(k["code"]) == 6


def test_incorrect_email():
    """Запрос кода на некорректный e-mail"""
    r = requests.post(f"{BASE}/api/auth/request-code", json={"email": ""})
    assert r.status_code == 400


def test_valid_verification_code():
    """верификация с правильным кодом"""
    email = "kkaplin64@gmail.com"
    r = requests.post(f"{BASE}/api/auth/request-code", json={"email": email})
    code = r.json()["code"]

    response = requests.post(f"{BASE}/api/auth/verify", json={"email": email, "code": code})

    assert response.status_code == 200
    assert "token" in response.json()


def test_invalid_verification_code():
    """верификация с неправильным кодом"""
    email = "Kaplin64@gmail.com"
    requests.post(f"{BASE}/api/auth/request-code", json={"email": email})
    response = requests.post(f"{BASE}/api/auth/verify", json={"email": email, "code": "000000"})
    assert response.status_code == 400


def test_profile_before_questionnaire(auth_headers):
    """Профиль недоступен до заполнения анкеты"""
    response = requests.get(f"{BASE}/api/profile", headers=auth_headers)
    assert response.status_code == 403
    assert "error" in response.json()


def test_questionnaire_success(auth_headers, user, valid_profile_data):
    """Успешное заполнение анкеты"""
    response = requests.post(f"{BASE}/api/questionnaire", headers=auth_headers, json=valid_profile_data)

    assert response.status_code == 201
    data = response.json()

    assert data["email"] == user["email"]
    assert data["first_name"] == valid_profile_data["first_name"]
    assert data["last_name"] == valid_profile_data["last_name"]
    assert data["age"] == valid_profile_data["age"]
    assert data["city"] == valid_profile_data["city"]
    assert data["bio"] == valid_profile_data["bio"]


@pytest.mark.parametrize("field, value, expected_error", [
    ("first_name", "", "Поле 'first_name' обязательно"),
    ("last_name", "", "Поле 'last_name' обязательно"),
    ("city", "", "Поле 'city' обязательно"),
    ("age", 0, "Возраст должен быть в диапазоне 1–119"),
    ("age", 120, "Возраст должен быть в диапазоне 1–119"),
    ("age", -1, "Возраст должен быть в диапазоне 1–119"),
    ("age", "abc", "Возраст должен быть числом"),
])
def test_questionnaire_validation(auth_headers, valid_profile_data, field, value, expected_error):
    """Валидация: пустые поля и некорректный возраст"""
    data = {**valid_profile_data, field: value}

    response = requests.post(f"{BASE}/api/questionnaire", headers=auth_headers, json=data)

    assert response.status_code == 400
    assert expected_error in response.json().get("error", "")


def test_get_profile_success(auth_headers, user, valid_profile_data):
    """Получение профиля с токеном"""
    response = requests.post(f"{BASE}/api/questionnaire", headers=auth_headers, json=valid_profile_data)
    assert response.status_code == 201

    response = requests.get(f"{BASE}/api/profile", headers=auth_headers)
    assert response.status_code == 200
    profile = response.json()
    assert profile["email"] == user["email"]
    assert profile["first_name"] == valid_profile_data["first_name"]
    assert profile["last_name"] == valid_profile_data["last_name"]
    assert profile["age"] == valid_profile_data["age"]
    assert profile["city"] == valid_profile_data["city"]
    assert profile["bio"] == valid_profile_data["bio"]


def test_get_profile_without_token():
    """Запрос профиля без токена"""
    response = requests.get(f"{BASE}/api/profile")
    assert response.status_code == 401
    assert "error" in response.json()


def test_update_profile_city(auth_headers, valid_profile_data):
    """Редактирование профиля"""
    response = requests.post(f"{BASE}/api/questionnaire", headers=auth_headers, json=valid_profile_data)
    assert response.status_code == 201

    new_city = "Казань"
    response = requests.patch(f"{BASE}/api/profile", headers=auth_headers, json={"city": new_city})
    assert response.status_code == 200
    assert response.json()["city"] == new_city

    check_response = requests.get(f"{BASE}/api/profile", headers=auth_headers)
    assert check_response.status_code == 200
    assert check_response.json()["city"] == new_city