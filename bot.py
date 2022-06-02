from vkbottle.bot import Bot, BotLabeler, Message
from vkbottle import VKAPIError
import sqlite3
from datetime import datetime, timedelta
from dateparser import parse
from random import randint
import asyncio
from config import token

async def main():
    """Основная функция бота. В ней скрипт ждёт от пользователя или беседы сообщения и обрабатывает их."""
    @bot.on.message(text=["/добавить <deadline> на <time>", "/добавь <deadline> на <time>", "дед, добавь <deadline> на <time>"])
    @bot.on.private_message(text=["добавить <deadline> на <time>", "добавь <deadline> на <time>"])
    async def setDeadline(message: Message, deadline: str, time: str):
        """Добавляет дедлайн для чата.
Кроме собственно сообщения принимает параметры `deadline` (str) - название дедлайна, а также `time` (str) - дату и время."""
        deadline = deadline.replace("дедлайн ", "") # Убирает слово "дедлайн", если пользователь ввёл его
        time = unifyTime(time)
        if time == None:
            await message.answer("Ошибка: неправильный формат даты и времени")
            return
        row = {"chat": message.peer_id, "deadline": deadline, "time": time}
        if message.from_id == message.peer_id: # Трюк, чтобы проверить, пришло сообщение из группового или одиночного чата
            row["isGroup"] = False
        else:
            row["isGroup"] = True
        cur.execute("INSERT INTO Deadlines VALUES(:chat, :deadline, :time, :isGroup);", row)
        database.commit()
        await message.answer(f"Готово, добавил дедлайн <<{deadline}>> на {time}")

    @bot.on.message(text=["/удалить <deadline>", "/удали <deadline>", "дед, удали <deadline>"])
    @bot.on.private_message(text=["удалить <deadline>", "удали <deadline>"])
    async def removeDeadline(message: Message, deadline: str):
        """Удаляет дедлайн для чата.
Кроме собственно сообщения принимает параметр `deadline` (str) - название дедлайна.
Если для чата задано несколько дедлайнов с одинаковым названием, будет удалён тот, который добавлен раньше."""
        deadline = deadline.replace("дедлайн ", "")
        deadline = cur.execute("SELECT ROWID, deadline FROM Deadlines WHERE chat=? AND deadline=? COLLATE NOCASE;", (message.peer_id, deadline)).fetchone()
        if deadline == None:
            pronoun = "тебя" if message.from_id == message.peer_id else "вас" # Делаем разные местоимения в зависимости от типа чата
            await message.answer(f"У {pronoun} нет такого дедлайна")
        else:
            cur.execute("DELETE FROM Deadlines WHERE ROWID=?;", (deadline[0],))
            database.commit()
            # Мы не используем `DELETE FROM Deadlines WHERE` сразу, так как у пользователя может быть несколько дедлайнов с одинаковым названием.
            await message.answer(f"Готово, удалил дедлайн <<{deadline[1]}>>")

    @bot.on.message(text=["/изменить <deadline> на <time>", "/измени <deadline> на <time>", "дед, измени <deadline> на <time>"])
    @bot.on.private_message(text=["изменить <deadline> на <time>", "измени <deadline> на <time>"])
    async def changeDeadline(message: Message, deadline: str, time: str):
        """Изменяет уже существующий дедлайн.
Кроме собственно сообщения принимает параметры `deadline` (str) - название изменяемого дедлайна, а также `time` (str) - новое время дедлайна.
Если для чата задано несколько дедлайнов с одинаковым названием, будет изменён тот, который добавлен раньше."""
        deadline = deadline.replace("дедлайн ", "")
        time = unifyTime(time)
        if time == None:
            await message.answer("Ошибка: неправильный формат даты и времени")
            return
        deadline = cur.execute("SELECT ROWID, deadline FROM Deadlines WHERE chat=? AND deadline=? COLLATE NOCASE;", (message.peer_id, deadline)).fetchone()
        if deadline == None:
            pronoun = "тебя" if message.from_id == message.peer_id else "вас"
            await message.answer(f"У {pronoun} нет такого дедлайна")
        else:
            cur.execute("UPDATE Deadlines SET time=? WHERE ROWID=?;", (time, deadline[0]))
            database.commit()
            await message.answer(f"Готово, изменил дедлайн <<{deadline[1]}>> на {time}")

    @bot.on.message(text=["/сбросить", "/сбрось", "дед, сбрось"])
    @bot.on.private_message(text=["сбросить", "сбрось"])
    async def clearDeadlines(message: Message):
        """Удаляет все дедлайны для данного чата."""
        cur.execute("DELETE FROM Deadlines WHERE chat=?;", (message.peer_id,))
        database.commit()
        await message.answer("Готово, удалил все дедлайны")

    @bot.on.message(text=["/дедлайны", "/скажи дедлайны", "/расскажи про дедлайны", "/что по дедлайнам", "/что по дедлайнам?", "дед, скажи дедлайны", "дед, расскажи про дедлайны", "дед, что по дедлайнам", "дед, что по дедлайнам?"])
    @bot.on.private_message(text=["дедлайны", "скажи дедлайны", "расскажи про дедлайны", "что по дедлайнам", "что по дедлайнам?"])
    async def sendDeadlines(message: Message):
        """Отправляет список текущих дедлайнов для данного чата."""
        deadlines = cur.execute("SELECT deadline, time FROM Deadlines WHERE chat=?;", (message.peer_id,)).fetchall()
        if len(deadlines) == 0:
            pronoun = "тебя" if message.from_id == message.peer_id else "вас"
            await message.answer(f"У {pronoun} нет текущих дедлайнов")
        else:
            answer = ""
            for deadline in deadlines:
                answer += f"""Дедлайн: {deadline[0]}
Когда: {deadline[1]}

"""
            await message.answer(answer)
    @bot.on.message(text=["/когда <deadline>?", "/когда <deadline>", "дед, когда <deadline>?", "дед, когда <deadline>"])
    @bot.on.private_message(text=["когда <deadline>?", "когда <deadline>"])
    async def whenDeadline(message: Message, deadline: str):
        """Сообщает время конкретного дедлайна.
Кроме собственно сообщения принимает параметр `deadline` (str) - название дедлайна.
Если для чата задано несколько дедлайнов с одинаковым названием, будет отправлена информация по тому, который задан раньше."""
        deadline = deadline.replace("дедлайн ", "")
        deadline = cur.execute("SELECT deadline, time FROM Deadlines WHERE chat=? AND deadline=? COLLATE NOCASE;", (message.peer_id, deadline)).fetchone()
        if deadline == None:
            pronoun = "тебя" if message.from_id == message.peer_id else "вас"
            await message.answer(f"У {pronoun} нет такого дедлайна")
        else:
            await message.answer(f"{deadline[0]}: {deadline[1]}")

    await asyncio.gather(bot.run_polling(), scheduler()) # Запускаем одновременно и бота, и планировщик

def unifyTime(time: str):
    """Приводит введённое пользователем время к формату 'dd.mm.yyyy HH:MM'. Возвращает строку. Если время распознать не удалось, возвращает `None`."""
    time = time.strip()    
    time = time.lower()
    time = parse(time, languages=["ru"], settings={
        "DATE_ORDER": "DMY", # Переопределяет порядок элементов даты для неочевидных дат
        "PREFER_DATES_FROM": "future" # Будет ориентироваться на ближайшее будущее для незавершённых дат
    })
    if not time:
        return None
    time = time.strftime("%d.%m.%Y %H:%M")
    return time

def ignore_case_collation(value1_: str, value2_: str):
    """Добавляет поддержку регистронезависимого сравнения кириллицы в SQLite."""
    if value1_.lower() == value2_.lower():
        return 0
    elif value1_.lower() < value2_.lower():
        return -1
    else:
        return 1

async def scheduler():
    """В фоновом режиме отправляет сообщение в чат, для которого установлен дедлайн, если текущее время совпадает с временем дедлайна или отличается (в меньшую сторону) на час или на сутки."""
    while True:
        timeFormat = "%d.%m.%Y %H:%M"
        today = datetime.today()
        currentTime = today.strftime(timeFormat)
        hourAfterTime = (today + timedelta(seconds=3600)).strftime(timeFormat)
        dayAfterTime = (today + timedelta(days=1)).strftime(timeFormat)
        deadlines = cur.execute("SELECT ROWID, chat, deadline, time, isGroup FROM Deadlines WHERE time=? OR time=? OR time=?;", (currentTime, hourAfterTime, dayAfterTime)).fetchall() # Выбираем только те дедлайны, которые установлены на интересующее нас время
        for deadline in deadlines:
            if deadline[3] == currentTime:
                await send(deadline[1], f"{deadline[2]}: время истекло")
                cur.execute("DELETE FROM Deadlines WHERE ROWID=?;", (deadline[0],))  # Удаляем истёкший дедлайн
                database.commit()
            elif deadline[3] == hourAfterTime:
                message = f"{deadline[2]}: остался 1 час до дедлайна ({deadline[3]})"
                if deadline[4]:
                    message = "@all\n" + message # Если дедлайн установлен для беседы, упоминаем всех её участников
                await send(deadline[1], message)
            elif deadline[3] == dayAfterTime:
                message = f"{deadline[2]}: остался 1 день до дедлайна ({deadline[3]})"
                if deadline[4]:
                    message = "@all\n" + message
                await send(deadline[1], message)
        await asyncio.sleep(60 - datetime.today().second) # До конца минуты новых дедлайнов точно не будет, можно не проверять

async def send(id: int, message: str):
    """Отправляет сообщение в чат. Принимает ID чата (int) и текст сообщения (str)."""
    try:
        await bot.api.messages.send(peer_id=id, random_id=randint(-2147483648, 2147483647), message=message, disable_mentions=0)
    except VKAPIError:
        return

bot = Bot(token)
bot.labeler.vbml_ignore_case = True # Делает обработчики сообщений регистронезависимыми
bot.labeler.load(BotLabeler())

database = sqlite3.connect("deadlines.db")
database.create_collation("NOCASE", ignore_case_collation) # Правило регистронезависимого сравнения для SQLite
cur = database.cursor()
cur.execute("""CREATE TABLE IF NOT EXISTS Deadlines(
    chat INT,
    deadline TEXT,
    time TEXT,
    isGroup INT
);""")
database.commit()

if __name__ == "__main__":
    asyncio.run(main())
