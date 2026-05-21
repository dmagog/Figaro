# language: ru
"""Шаги для security.feature (этап 3): согласие, верификация, сброс, lockout, CSRF, удаление."""
from datetime import date, datetime, timedelta

from behave import given, then, when
from sqlmodel import select

from figaro.domain.models import RouteSheet, User, UserPreferences
from figaro.importing import source as S
from figaro.importing.seed import import_catalog
from figaro.services import auth
from figaro.services.auth import researcher_customer_aggregates
from figaro.services.festival import create_festival

BASE = datetime(2026, 1, 1, 12, 0)  # naive UTC


def _festival(context):
    if context.festival is None:
        context.festival = create_festival(context.session, name="2026", year=2026,
                                           sales_start_on=date(2026, 6, 1),
                                           starts_on=date(2026, 7, 1), ends_on=date(2026, 7, 3))
    return context.festival


# --- согласие ---
@given('я заполняю форму регистрации')
def step_fill_form(context):
    context.reg_email = "consent@example.com"


@when('я отправляю её без согласия на обработку персональных данных')
def step_submit_no_consent(context):
    context.consent_error = None
    try:
        auth.register(context.session, email=context.reg_email, password="pw", consent=False)
    except auth.ConsentRequired as e:
        context.consent_error = e


@then('регистрация отклонена')
def step_registration_rejected(context):
    assert isinstance(context.consent_error, auth.ConsentRequired)


@when('я отправляю её с согласием')
def step_submit_consent(context):
    context.user = auth.register(context.session, email=context.reg_email, password="pw",
                                 consent=True, now=BASE)


@then('аккаунт создан и зафиксировано время согласия')
def step_account_created(context):
    assert context.user.id is not None and context.user.consent_at is not None


# --- псевдонимизация в аналитике ---
@given('есть пользователи с email и покупками')
def step_users_with_purchases(context):
    f = _festival(context)
    auth.register(context.session, email="a@example.com", password="pw", consent=True)
    src = S.CatalogSource(
        halls=[S.HallRow("A", seats=100)],
        concerts=[S.ConcertRow(1, 42, "K", "A", datetime(2026, 7, 1, 13, 0), 45)],
        purchases=[S.PurchaseRow(1, "client-1", 42, datetime(2026, 6, 20, 10, 0)),
                   S.PurchaseRow(2, "client-2", 42, datetime(2026, 6, 21, 10, 0))])
    import_catalog(context.session, f.id, src)


@when('исследователь открывает дашборды')
def step_researcher_dashboards(context):
    context.agg = researcher_customer_aggregates(context.session)


@then('он видит агрегаты и псевдонимы, но не email и не имена')
def step_no_pii(context):
    assert context.agg
    for row in context.agg:
        assert set(row.keys()) == {"customer", "purchases"}
        assert "email" not in row and "name" not in row


# --- верификация email ---
@given('я зарегистрировался с email "{email}"')
def step_registered(context, email):
    context.user = auth.register(context.session, email=email, password="pw", consent=True)
    context.vtoken = auth.request_email_verification(context.session, context.user)


@when('я подтверждаю email по ссылке из письма')
def step_verify(context):
    auth.verify_email(context.session, context.vtoken)


@then('мой аккаунт помечен подтверждённым')
def step_verified(context):
    context.session.refresh(context.user)
    assert context.user.email_verified


# --- сброс пароля ---
@when('я запрашиваю сброс пароля')
def step_request_reset(context):
    context.rtoken = auth.request_password_reset(context.session, context.email,
                                                 ttl_minutes=60, now=BASE)


@when('перехожу по ссылке из письма в пределах срока её действия')
def step_within_ttl(context):
    context.reset_now = BASE + timedelta(minutes=10)


@when('задаю новый пароль')
def step_set_new_password(context):
    auth.reset_password(context.session, context.rtoken, "newpw", now=context.reset_now)


@then('я могу войти с новым паролем')
def step_login_new(context):
    u = auth.authenticate(context.session, email=context.email, password="newpw")
    assert u is not None


@given('я запросил сброс пароля')
def step_requested_reset(context):
    context.email = "reset@example.com"
    auth.register(context.session, email=context.email, password="pw", consent=True)
    context.rtoken = auth.request_password_reset(context.session, context.email,
                                                 ttl_minutes=60, now=BASE)


@when('срок действия ссылки истёк')
def step_ttl_expired(context):
    context.reset_now = BASE + timedelta(minutes=61)


@when('я перехожу по ней')
def step_follow_expired(context):
    context.reset_error = None
    try:
        auth.reset_password(context.session, context.rtoken, "newpw", now=context.reset_now)
    except auth.AuthError as e:
        context.reset_error = e


@then('сброс отклонён')
def step_reset_rejected(context):
    assert context.reset_error is not None


# --- защита от перебора ---
@when('подряд выполняется много неудачных попыток входа')
def step_brute_force(context):
    for _ in range(auth.LOCK_THRESHOLD):
        try:
            auth.authenticate(context.session, email=context.email, password="WRONG", now=BASE)
        except auth.AuthError:
            pass


@then('дальнейшие попытки временно блокируются')
def step_locked(context):
    context.locked = False
    try:
        auth.authenticate(context.session, email=context.email, password="pw", now=BASE)
    except auth.AccountLocked:
        context.locked = True
    except auth.AuthError:
        context.locked = False
    assert context.locked


# --- CSRF ---
@when('я отправляю POST-запрос на изменение листа без валидного CSRF-токена')
def step_post_no_csrf(context):
    context.csrf_error = None
    try:
        auth.verify_csrf(None, "expected-token")
    except auth.CsrfError as e:
        context.csrf_error = e


@then('запрос отклонён со статусом "403"')
def step_csrf_403(context):
    assert isinstance(context.csrf_error, auth.CsrfError)


# --- удаление аккаунта ---
@given('зритель с аккаунтом, анкетой и маршрутными листами')
def step_user_with_data(context):
    f = _festival(context)
    u = auth.register(context.session, email="del@example.com", password="pw", consent=True)
    context.del_user_id = u.id
    context.session.add(UserPreferences(user_id=u.id, festival_id=f.id, pace="balanced"))
    sheet = RouteSheet(user_id=u.id, festival_id=f.id, title="Мой лист")
    context.session.add(sheet)
    context.session.flush()


@when('он запрашивает удаление аккаунта')
def step_delete_account(context):
    auth.delete_account(context.session, context.del_user_id)


@then('аккаунт и его анкета и листы удалены')
def step_data_deleted(context):
    uid = context.del_user_id
    assert context.session.exec(select(UserPreferences).where(UserPreferences.user_id == uid)).first() is None
    assert context.session.exec(select(RouteSheet).where(RouteSheet.user_id == uid)).first() is None


@then('в данных не остаётся персональных сведений этого пользователя')
def step_no_pii_left(context):
    assert context.session.get(User, context.del_user_id) is None
