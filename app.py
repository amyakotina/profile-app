"""
Учебный проект «Профиль».

Возможности:
  - вход по e-mail: код авторизации возвращается прямо в ответе бэка
    (демо-режим, без реальной почты);
  - после входа — обязательная анкета;
  - затем профиль с редактированием.

Одно и то же приложение отдаёт JSON API (под /api) и обычные HTML-страницы,
поэтому к нему удобно писать и API-, и UI-тесты.

Запуск:
    pip install flask
    python app.py
    # открыть http://localhost:5001
"""

from flask import (Flask, request, jsonify, session,
                   redirect, url_for, render_template_string)

from core import AuthService

app = Flask(__name__)
app.secret_key = "dev-secret-not-for-production"
service = AuthService()


# =========================================================================
#  JSON API
# =========================================================================

def _bearer_token():
    auth = request.headers.get("Authorization", "")
    return auth[7:] if auth.startswith("Bearer ") else None


def _api_error(err):
    message, status = err
    return jsonify({"error": message}), status


@app.post("/api/auth/request-code")
def api_request_code():
    data = request.get_json(silent=True) or {}
    result, err = service.request_code(data.get("email"))
    if err:
        return _api_error(err)
    return jsonify({
        "email": result["email"],
        "code": result["code"],
        "message": "Код авторизации отправлен (демо: он в поле code)",
    }), 200


@app.post("/api/auth/verify")
def api_verify():
    data = request.get_json(silent=True) or {}
    result, err = service.verify_code(data.get("email"), data.get("code"))
    if err:
        return _api_error(err)
    return jsonify(result), 200


@app.post("/api/questionnaire")
def api_questionnaire():
    data = request.get_json(silent=True) or {}
    profile, err = service.submit_questionnaire(_bearer_token(), data)
    if err:
        return _api_error(err)
    return jsonify(profile), 201


@app.get("/api/profile")
def api_get_profile():
    profile, err = service.get_profile(_bearer_token())
    if err:
        return _api_error(err)
    return jsonify(profile), 200


@app.patch("/api/profile")
def api_update_profile():
    data = request.get_json(silent=True) or {}
    profile, err = service.update_profile(_bearer_token(), data)
    if err:
        return _api_error(err)
    return jsonify(profile), 200


# =========================================================================
#  HTML (UI) — тот же сервис, авторизация через cookie-сессию
# =========================================================================

BASE = """<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ title }}</title>
<style>
  body { font-family: system-ui, sans-serif; max-width: 480px; margin: 40px auto;
         padding: 0 16px; color: #1e1e1e; }
  h1 { font-size: 24px; }
  form { display: grid; gap: 12px; margin-top: 16px; }
  label { display: grid; gap: 4px; font-size: 14px; }
  input, textarea { padding: 8px; border: 1px solid #ccc; border-radius: 6px; font-size: 15px; }
  button { padding: 10px 16px; border: 0; border-radius: 6px; background: #ff4a1c;
           color: #fff; font-size: 15px; cursor: pointer; }
  .msg { background: #eef; padding: 10px 12px; border-radius: 6px; }
  .err { background: #fee; color: #a00; padding: 10px 12px; border-radius: 6px; }
  .code { font-size: 22px; font-weight: 700; letter-spacing: 2px; }
  .row { display: flex; justify-content: space-between; align-items: center; }
  a { color: #ff4a1c; }
  dl { display: grid; grid-template-columns: auto 1fr; gap: 6px 16px; }
  dt { color: #666; }
</style></head><body>
<h1>{{ title }}</h1>
{% if error %}<p class="err">{{ error }}</p>{% endif %}
{% if message %}<p class="msg">{{ message }}</p>{% endif %}
{{ body|safe }}
</body></html>"""


def render(title, body, **kw):
    return render_template_string(BASE, title=title, body=body, **kw)


@app.get("/")
def ui_index():
    token = session.get("token")
    if token and service.user_by_token(token) and service.user_by_token(token)["profile_completed"]:
        return redirect(url_for("ui_profile"))
    body = """
      <form method="post" action="/login">
        <label for="email">Email
          <input id="email" name="email" type="email" placeholder="you@example.com" required>
        </label>
        <button type="submit">Получить код</button>
      </form>"""
    return render("Вход", body, error=request.args.get("error"))


@app.post("/login")
def ui_login():
    email = request.form.get("email")
    result, err = service.request_code(email)
    if err:
        return redirect(url_for("ui_index", error=err[0]))
    session["pending_email"] = email
    session["demo_code"] = result["code"]
    return redirect(url_for("ui_verify"))


@app.get("/verify")
def ui_verify():
    email = session.get("pending_email")
    if not email:
        return redirect(url_for("ui_index"))
    body = """
      <p>Мы «отправили» код на <b>{email}</b>.
         В демо-режиме код показан здесь:</p>
      <p class="code" data-testid="demo-code">{code}</p>
      <form method="post" action="/verify">
        <label for="code">Код
          <input id="code" name="code" inputmode="numeric" required>
        </label>
        <button type="submit">Войти</button>
      </form>""".format(email=email, code=session.get("demo_code", ""))
    return render("Подтверждение", body, error=request.args.get("error"))


@app.post("/verify")
def ui_verify_post():
    email = session.get("pending_email")
    result, err = service.verify_code(email, request.form.get("code"))
    if err:
        return redirect(url_for("ui_verify", error=err[0]))
    session["token"] = result["token"]
    session.pop("pending_email", None)
    session.pop("demo_code", None)
    if result["profile_completed"]:
        return redirect(url_for("ui_profile"))
    return redirect(url_for("ui_questionnaire"))


@app.get("/questionnaire")
def ui_questionnaire():
    token = session.get("token")
    user = service.user_by_token(token)
    if not user:
        return redirect(url_for("ui_index"))
    if user["profile_completed"]:
        return redirect(url_for("ui_profile"))
    body = """
      <p>Чтобы получить доступ к профилю, заполните анкету.</p>
      <form method="post" action="/questionnaire">
        <label for="first_name">Имя <input id="first_name" name="first_name" required></label>
        <label for="last_name">Фамилия <input id="last_name" name="last_name" required></label>
        <label for="age">Возраст <input id="age" name="age" inputmode="numeric" required></label>
        <label for="city">Город <input id="city" name="city" required></label>
        <label for="bio">О себе <textarea id="bio" name="bio" rows="3"></textarea></label>
        <button type="submit">Сохранить анкету</button>
      </form>"""
    return render("Анкета", body, error=request.args.get("error"))


@app.post("/questionnaire")
def ui_questionnaire_post():
    token = session.get("token")
    _, err = service.submit_questionnaire(token, request.form.to_dict())
    if err:
        return redirect(url_for("ui_questionnaire", error=err[0]))
    return redirect(url_for("ui_profile"))


@app.get("/profile")
def ui_profile():
    token = session.get("token")
    profile, err = service.get_profile(token)
    if err:
        # не авторизован -> на вход; анкета не заполнена -> на анкету
        if err[1] == 401:
            return redirect(url_for("ui_index"))
        return redirect(url_for("ui_questionnaire"))
    body = """
      <dl>
        <dt>Email</dt><dd data-testid="profile-email">{email}</dd>
        <dt>Имя</dt><dd data-testid="profile-first_name">{first_name}</dd>
        <dt>Фамилия</dt><dd data-testid="profile-last_name">{last_name}</dd>
        <dt>Возраст</dt><dd data-testid="profile-age">{age}</dd>
        <dt>Город</dt><dd data-testid="profile-city">{city}</dd>
        <dt>О себе</dt><dd data-testid="profile-bio">{bio}</dd>
      </dl>
      <h1>Редактировать</h1>
      <form method="post" action="/profile">
        <label for="e_first_name">Имя <input id="e_first_name" name="first_name" value="{first_name}"></label>
        <label for="e_last_name">Фамилия <input id="e_last_name" name="last_name" value="{last_name}"></label>
        <label for="e_age">Возраст <input id="e_age" name="age" value="{age}"></label>
        <label for="e_city">Город <input id="e_city" name="city" value="{city}"></label>
        <label for="e_bio">О себе <textarea id="e_bio" name="bio" rows="3">{bio}</textarea></label>
        <button type="submit">Сохранить изменения</button>
      </form>
      <p class="row"><span></span><a href="/logout">Выйти</a></p>""".format(**profile)
    return render("Профиль", body,
                  message=request.args.get("message"),
                  error=request.args.get("error"))


@app.post("/profile")
def ui_profile_post():
    token = session.get("token")
    _, err = service.update_profile(token, request.form.to_dict())
    if err:
        return redirect(url_for("ui_profile", error=err[0]))
    return redirect(url_for("ui_profile", message="Профиль обновлён"))


@app.get("/logout")
def ui_logout():
    session.clear()
    return redirect(url_for("ui_index"))


if __name__ == "__main__":
    # порт 5001, а не 5000: на macOS 5000 часто занят сервисом AirPlay Receiver
    import os
    port = int(os.environ.get("PORT", "5001"))
    app.run(host="127.0.0.1", port=port, debug=True)
