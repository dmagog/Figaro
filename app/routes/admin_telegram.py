from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from models.user import User
from database.database import get_session
from sqlmodel import select
import asyncio
import sys
sys.path.append("../../bot")
from bot.utils import send_telegram_message

admin_telegram_router = APIRouter()

@admin_telegram_router.get("/admin/telegram", response_class=HTMLResponse)
async def admin_telegram_page(request: Request, session=Depends(get_session)):
    current_user = request.state.user if hasattr(request.state, 'user') else None
    if not current_user or not getattr(current_user, 'is_superuser', False):
        return RedirectResponse(url="/login")
    context = {"request": request}
    return request.app.templates.TemplateResponse("admin_telegram.html", context)

@admin_telegram_router.post("/admin/send-telegram")
async def send_telegram(request: Request, session=Depends(get_session)):
    data = await request.json()
    user_id = data.get("user_id")
    telegram_id = data.get("telegram_id")
    message = data.get("message")
    if not message:
        return JSONResponse({"success": False, "error": "Текст сообщения обязателен"}, status_code=400)
    current_user = request.state.user if hasattr(request.state, 'user') else None
    if not current_user or not getattr(current_user, 'is_superuser', False):
        raise HTTPException(status_code=403, detail="Только для админов")
    if not telegram_id:
        if not user_id:
            return JSONResponse({"success": False, "error": "Нужно указать user_id или telegram_id"}, status_code=400)
        user = session.exec(select(User).where(User.id == user_id)).first()
        if not user or not user.telegram_id:
            return JSONResponse({"success": False, "error": "Пользователь не найден или не привязан к Telegram"}, status_code=404)
        telegram_id = user.telegram_id
    ok = await send_telegram_message(telegram_id, text=message)
    if ok:
        return {"success": True}
    else:
        return JSONResponse({"success": False, "error": "Ошибка отправки сообщения"}, status_code=500) 