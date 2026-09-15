import os

from playwright.sync_api import Page, expect

BASE = os.environ.get("APP_BASE", "http://127.0.0.1:5001")


def test_happy_path_login_questionnaire_profile(login_as, fill_questionnaire, logout, unique_email, page: Page):
    """Полный happy-path"""

    # 1-2. вход по email + код
    login_as(unique_email)
    expect(page).to_have_url(f"{BASE}/questionnaire")

    # 3. заполняем анкету
    fill_questionnaire("Иван", "Петров", 25, "Москва", "Пользователь")
    expect(page).to_have_url(f"{BASE}/profile")

    # 4. профиль доступен и содержит наши данные
    expect(page.get_by_role("heading", name="Профиль")).to_be_visible()
    expect(page.get_by_test_id("profile-first_name")).to_have_text("Иван")
    expect(page.get_by_test_id("profile-last_name")).to_have_text("Петров")
    expect(page.get_by_test_id("profile-age")).to_have_text("25")
    expect(page.get_by_test_id("profile-city")).to_have_text("Москва")
    expect(page.locator("dt:has-text('О себе') + dd")).to_have_text("Пользователь")

    # 5. форма редактирования присутствует
    expect(page.get_by_label("Имя")).to_be_visible()
    expect(page.get_by_label("Фамилия")).to_be_visible()
    expect(page.get_by_label("Возраст")).to_be_visible()
    expect(page.get_by_label("Город")).to_be_visible()
    expect(page.get_by_label("О себе")).to_be_visible()
    expect(page.get_by_role("button", name="Сохранить изменения")).to_be_visible()

    # 6. редактируем профиль
    fill_questionnaire("Петр", "Иванов", 45, "Казань", "Пользователь2", save_button="Сохранить изменения")

    # 7. изменения отобразились
    expect(page.get_by_role("heading", name="Профиль")).to_be_visible()
    expect(page.get_by_test_id("profile-first_name")).to_have_text("Петр")
    expect(page.get_by_test_id("profile-last_name")).to_have_text("Иванов")
    expect(page.get_by_test_id("profile-age")).to_have_text("45")
    expect(page.get_by_test_id("profile-city")).to_have_text("Казань")
    expect(page.locator("dt:has-text('О себе') + dd")).to_have_text("Пользователь2")

    # 8. выход
    logout()
    expected_url = BASE.rstrip("/")
    assert page.url.rstrip("/") == expected_url, f"Expected {expected_url}, but got {page.url}"

    # 9. данные сохраняются при повторном входе
    login_as(unique_email)
    expect(page).to_have_url(f"{BASE}/profile")


def test_request_without_a_registered_profile(login_as, unique_email, page: Page):
    """Пользователь без профиля должен быть перенаправлен на анкету"""
    login_as(unique_email)
    expect(page).to_have_url(f"{BASE}/questionnaire")

    try:
        expect(page.get_by_test_id("questionnaire-message")).to_have_text(
            "Для доступа к профилю необходимо заполнить анкету"
        )
    except AssertionError:
        expect(page.get_by_role("heading", name="Анкета")).to_be_visible()


def test_editing_profile_reflected_page(login_as, fill_questionnaire, unique_email, page: Page):
    """Редактирование профиля отражается на странице"""
    login_as(unique_email)

    fill_questionnaire("Иван", "Петров", 25, "Москва", "Пользователь")
    expect(page).to_have_url(f"{BASE}/profile")

    fill_questionnaire("Петр", "Иванов", 45, "Казань", "Пользователь2", save_button="Сохранить изменения")

    expect(page.get_by_role("heading", name="Профиль")).to_be_visible()
    expect(page.get_by_test_id("profile-first_name")).to_have_text("Петр")
    expect(page.get_by_test_id("profile-last_name")).to_have_text("Иванов")
    expect(page.get_by_test_id("profile-age")).to_have_text("45")
    expect(page.get_by_test_id("profile-city")).to_have_text("Казань")
    expect(page.locator("dt:has-text('О себе') + dd")).to_have_text("Пользователь2")