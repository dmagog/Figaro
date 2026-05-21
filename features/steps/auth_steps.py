# language: ru
"""Шаги для auth_roles.feature (этап 3). Также общие auth-шаги для security.feature."""
from datetime import date

from behave import given, then, when

from figaro.domain.models import RouteSheet
from figaro.services import auth
from figaro.services.festival import create_festival


def _user(context, email, role="user", pw="pw"):
    u = auth.register(context.session, email=email, password=pw, consent=True)
    if role != "user":
        u.role = role
        context.session.add(u)
        context.session.flush()
    return u


def _festival(context):
    if context.festival is None:
        context.festival = create_festival(context.session, name="2026", year=2026,
                                           sales_start_on=date(2026, 6, 1),
                                           starts_on=date(2026, 7, 1), ends_on=date(2026, 7, 3))
    return context.festival


# --- регистрация / вход ---
@given('я регистрируюсь с email "{email}" и паролем')
def step_register(context, email):
    context.email, context.password = email, "pw"
    auth.register(context.session, email=email, password="pw", consent=True)


@when('я вхожу с этими данными')
def step_login(context):
    context.user = auth.authenticate(context.session, email=context.email, password=context.password)


@then('я аутентифицирован как роль "{role}"')
def step_auth_role(context, role):
    assert context.user.role == role, context.user.role


@given('есть пользователь "{email}"')
def step_user_exists(context, email):
    context.email, context.password = email, "pw"
    _user(context, email)


@when('я вхожу с неверным паролем')
def step_login_bad(context):
    context.auth_error = None
    try:
        auth.authenticate(context.session, email=context.email, password="WRONG")
    except auth.AuthError as e:
        context.auth_error = e


@then('вход отклонён')
def step_login_rejected(context):
    assert context.auth_error is not None


# --- RBAC ---
@given('пользователь с ролью "{role}"')
def step_role(context, role):
    context.role = role


@when('он открывает раздел "{area}"')
def step_open_area(context, area):
    context.area = area


@then('доступ "{result}"')
def step_access(context, result):
    expected = result.strip() == "разрешён"
    assert auth.can_access(context.role, context.area) == expected, (context.role, context.area)


@given('я вошёл как "{role}"')
def step_logged_in_as(context, role):
    context.actor = _user(context, f"{role}@example.com", role=role)


@given('существует пользователь "{email}" с ролью "{role}"')
def step_user_with_role(context, email, role):
    _user(context, email, role=role)


@when('я меняю роль пользователя "{email}" на "{role}"')
def step_change_role(context, email, role):
    auth.change_role(context.session, actor=context.actor, target_email=email, new_role=role)


@then('роль пользователя "{email}" — "{role}"')
def step_assert_role(context, email, role):
    from sqlmodel import select

    from figaro.domain.models import User
    u = context.session.exec(select(User).where(User.email == email)).first()
    assert u.role == role, u.role


# --- сессии / выход ---
@given('я вошёл как зритель')
def step_logged_in_viewer(context):
    context.actor = _user(context, "viewer@example.com")
    context.token = auth.create_session(context.session, context.actor)


@when('я выхожу из аккаунта')
def step_logout(context):
    auth.logout(context.session, context.token)


@when('открываю страницу, требующую входа')
def step_open_protected(context):
    context.session_user = auth.user_for_session(context.session, context.token)


@when('я открываю страницу, требующую входа')
def step_open_protected2(context):
    context.session_user = auth.user_for_session(context.session, context.token)


@given('срок сессии истёк')
def step_session_expired(context):
    context.token = auth.create_session(context.session, context.actor, ttl_minutes=-1)


@then('меня перенаправляет на вход')
def step_redirect_login(context):
    assert context.session_user is None


# --- владение ресурсом ---
@given('зритель "{email}" владеет маршрутным листом "{title}"')
def step_owner_sheet(context, email, title):
    owner = _user(context, email)
    fest = _festival(context)
    sheet = RouteSheet(user_id=owner.id, festival_id=fest.id, title=title)
    context.session.add(sheet)
    context.session.flush()
    context.sheet = sheet


@given('вошёл другой зритель "{email}"')
def step_other_viewer(context, email):
    context.other = _user(context, email)


@when('"{email}" пытается изменить лист "{title}"')
def step_other_edits(context, email, title):
    context.forbidden = None
    try:
        auth.assert_can_edit_sheet(context.other.id, context.sheet)
    except auth.Forbidden as e:
        context.forbidden = e


@then('доступ запрещён со статусом "403"')
def step_forbidden_403(context):
    assert isinstance(context.forbidden, auth.Forbidden)
