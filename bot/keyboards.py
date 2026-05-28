from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def score_keyboard(prefix: str) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text=str(i), callback_data=f"{prefix}:{i}")
            for i in range(1, 6)
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def yes_no_keyboard(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Да", callback_data=f"{prefix}:yes"),
                InlineKeyboardButton(text="Нет", callback_data=f"{prefix}:no"),
            ]
        ]
    )


def clients_page_keyboard(
    clients: list[dict],
    selected_ids: set[int],
    page: int,
    total_pages: int,
    prefix: str = "clnt",
) -> InlineKeyboardMarkup:
    rows = []
    for cl in clients:
        mark = "✅ " if cl["id"] in selected_ids else ""
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{mark}{cl['name']}",
                    callback_data=f"{prefix}:toggle:{cl['id']}",
                )
            ]
        )

    nav = []
    if page > 0:
        nav.append(
            InlineKeyboardButton(
                text="← Назад", callback_data=f"{prefix}:page:{page - 1}"
            )
        )
    if page < total_pages - 1:
        nav.append(
            InlineKeyboardButton(
                text="Вперёд →", callback_data=f"{prefix}:page:{page + 1}"
            )
        )
    if nav:
        rows.append(nav)

    if selected_ids:
        rows.append(
            [
                InlineKeyboardButton(
                    text="✅ Готово", callback_data=f"{prefix}:done"
                )
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=rows)


def continue_restart_keyboard(prefix: str = "survey") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Продолжить", callback_data=f"{prefix}:continue"
                ),
                InlineKeyboardButton(
                    text="Начать заново", callback_data=f"{prefix}:restart"
                ),
            ]
        ]
    )


def reminder_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Продолжить опрос", callback_data="survey:continue")]
        ]
    )


def changed_clients_keyboard(prefix: str = "clnt") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Да", callback_data=f"{prefix}:changed:yes"),
                InlineKeyboardButton(text="Нет", callback_data=f"{prefix}:changed:no"),
            ]
        ]
    )


def update_client_keyboard(clients: list) -> InlineKeyboardMarkup:
    rows = []
    for c in clients:
        rows.append([InlineKeyboardButton(
            text=c.name,
            callback_data=f"upd:select:{c.id}",
        )])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def update_again_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Обновить ещё", callback_data="upd:again"),
                InlineKeyboardButton(text="Готово", callback_data="upd:done"),
            ]
        ]
    )