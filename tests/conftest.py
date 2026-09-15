import os
import uuid

import pytest
import requests
from playwright.sync_api import Page, expect

BASE = os.environ.get("APP_BASE", "http://127.0.0.1:5001")


@pytest.fixture
def user():
    """Данные тестового пользователя

    Email каждый раз новый: приложение не сбрасывает состояние между
    запусками тестов, а фиксированный email одного теста к другому
    делает профиль "уже заполненным" в следующих прогонах."""
    return {
        "email": f"user_{uuid.uuid4().hex[:12]}@example.com",
        "name": "Иван",
        "surname": "Петров",
    }


@pytest.fixture
def valid_profile_data(user):
    """Валидные данные анкеты"""
    return {
        "first_name": user["name"],
        "last_name": user["surname"],
        "age": 25,
        "city": "Саратов",
        "bio": "Тестовый пользователь",
    }


@pytest.fixture
def unique_email():
    """Email, уникальный для каждого теста"""
    return f"test_{uuid.uuid4().hex[:12]}@example.com"


@pytest.fixture
def auth_headers(user):
    """Токен авторизации для API-тестов"""
    r = requests.post(f"{BASE}/api/auth/request-code", json={"email": user["email"]})
    assert r.status_code == 200
    code = r.json()["code"]

    response = requests.post(
        f"{BASE}/api/auth/verify", json={"email": user["email"], "code": code}
    )
    assert response.status_code == 200
    token = response.json()["token"]

    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def login_as(page: Page):
    """login_as(email) -> Page, залогиненная под указанный e-mail"""

    def _login(email: str):
        page.goto(BASE)
        page.get_by_label("Email").fill(email)
        page.get_by_role("button", name="Получить код").click()
        expect(page).to_have_url(f"{BASE}/verify")

        code = page.get_by_test_id("demo-code").inner_text()
        page.get_by_label("Код").fill(code)
        page.get_by_role("button", name="Войти").click()
        return page

    return _login


@pytest.fixture
def fill_questionnaire(page: Page):
    """Заполняет анкету или форму редактирования профиля"""

    def _fill(first_name, last_name, age, city, bio, save_button="Сохранить анкету"):
        page.get_by_label("Имя").fill(first_name)
        page.get_by_label("Фамилия").fill(last_name)
        page.get_by_label("Возраст").fill(str(age))
        page.get_by_label("Город").fill(city)
        page.get_by_label("О себе").fill(bio)
        page.get_by_role("button", name=save_button).click()
        return page

    return _fill


@pytest.fixture
def logout(page: Page):
    """Разлогинивает пользователя, учитывая разные варианты реализации кнопки выхода"""

    def _logout():
        for attempt in (
            lambda: page.get_by_role("button", name="Выйти").click(timeout=1000),
            lambda: page.get_by_role("link", name="Выйти").click(timeout=1000),
            lambda: page.get_by_text("Выйти").click(timeout=1000),
        ):
            try:
                attempt()
                return
            except Exception:
                continue
        page.goto(f"{BASE}/logout")

    return _logout


@pytest.fixture
def authenticated_page(login_as, user):
    """Страница, залогиненная под тестового пользователя, до заполнения анкеты"""
    page = login_as(user["email"])
    expect(page).to_have_url(f"{BASE}/questionnaire")
    return page


@pytest.fixture
def profile_page(authenticated_page, fill_questionnaire):
    """Страница профиля с уже заполненной анкетой"""
    fill_questionnaire("Иван", "Петров", 25, "Москва", "Пользователь")
    expect(authenticated_page).to_have_url(f"{BASE}/profile")
    return authenticated_page