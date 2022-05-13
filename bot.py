from vkbottle.bot import Bot, BotLabeler, Message
from config import token
import sqlite3
import re
from datetime import datetime, timedelta

def main():
    """Основная функция бота. В ней скрипт ждёт от пользователя или беседы сообщения и обрабатывает их."""
    @bot.on.message(text="/добавить <deadline> на <time>")
    @bot.on.private_message(text="добавить <deadline> на <time>")
    async def setDeadline(message: Message, deadline: str, time: str):
        """Добавляет дедлайн для чата.
Кроме собственно сообщения принимает параметры `deadline` (str) - название дедлайна, а также `time` (str) - дату и время."""
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
        await message.answer(f"Дедлайн <<{deadline}>> установлен на {time}")

    @bot.on.message(text="/удалить <deadline>")
    @bot.on.private_message(text="удалить <deadline>")
    async def removeDeadline(message: Message, deadline: str):
        """Удаляет дедлайн для чата.
Кроме собственно сообщения принимает параметр `deadline` (str) - название дедлайна.
Если для чата задано несколько дедлайнов с одинаковым названием, будет удалён тот, который добавлен раньше."""
        deadline = cur.execute("SELECT ROWID, deadline FROM Deadlines WHERE chat=? AND deadline=? COLLATE NOCASE;", (message.peer_id, deadline)).fetchone()
        if deadline == None:
            pronoun = "тебя" if message.from_id == message.peer_id else "вас" # Делаем разные местоимения в зависимости от типа чата
            await message.answer(f"у {pronoun} нет такого дедлайна")
        else:
            cur.execute("DELETE FROM Deadlines WHERE ROWID=?;", (deadline[0],))
            database.commit()
            # Мы не используем `DELETE FROM Deadlines WHERE` сразу, так как у пользователя может быть несколько дедлайнов с одинаковым названием.
            await message.answer(f"Дедлайн <<{deadline[1]}>> удалён")

    @bot.on.message(text="/изменить <deadline> на <time>")
    @bot.on.private_message(text="изменить <deadline> на <time>")
    async def changeDeadline(message: Message, deadline: str, time: str):
        """Изменяет уже существующий дедлайн.
Кроме собственно сообщения принимает параметры `deadline` (str) - название изменяемого дедлайна, а также `time` (str) - новое время дедлайна.
Если для чата задано несколько дедлайнов с одинаковым названием, будет изменён тот, который добавлен раньше."""
        time = unifyTime(time)
        if time == None:
            await message.answer("Ошибка: неправильный формат даты и времени")
            return
        deadline = cur.execute("SELECT ROWID, deadline FROM Deadlines WHERE chat=? AND deadline=? COLLATE NOCASE;", (message.peer_id, deadline)).fetchone()
        if deadline == None:
            pronoun = "тебя" if message.from_id == message.peer_id else "вас"
            await message.answer(f"у {pronoun} нет такого дедлайна")
        else:
            cur.execute("UPDATE Deadlines SET time=? WHERE ROWID=?;", (time, deadline[0]))
            database.commit()
            await message.answer(f"Дедлайн <<{deadline[1]}>> изменён на {time}")

    @bot.on.message(text="/сбросить")
    @bot.on.private_message(text="сбросить")
    async def clearDeadlines(message: Message):
        """Удаляет все дедлайны для данного чата."""
        cur.execute("DELETE FROM Deadlines WHERE chat=?;", (message.peer_id,))
        database.commit()
        await message.answer("Все дедлайны удалены")

    @bot.on.message(text="/дедлайны")
    @bot.on.private_message(text="дедлайны")
    async def sendDeadlines(message: Message):
        """Отправляет список текущих дедлайнов для данного чата."""
        deadlines = cur.execute("SELECT deadline, time FROM Deadlines WHERE chat=?;", (message.peer_id,)).fetchall()
        if len(deadlines) == 0:
            pronoun = "тебя" if message.from_id == message.peer_id else "вас"
            await message.answer(f"у {pronoun} нет текущих дедлайнов")
        else:
            answer = ""
            for deadline in deadlines:
                answer += f"""Дедлайн: {deadline[0]}
Когда: {deadline[1]}

"""
            await message.answer(answer)

    bot.run_forever()

def unifyTime(time: str):
    """Приводит введённое пользователем время к формату 'dd.mm.yyyy HH:MM'. Возвращает строку."""
    validated = False
    time = time.strip()    
    time = time.lower()
    if re.fullmatch(r"\d\d:\d\d", time): # Проверяем, не ввёл ли пользователь время без даты
        time = datetime.strftime(datetime.today(), "%d.%m.%Y") + f" {time}"
    if re.match(r"завтра", time):
        time = time.replace("завтра", datetime.strftime(datetime.today() + timedelta(days=1), "%d.%m.%Y"))
    if not re.match(r"\d\d", time): # День месяца должен всегда занимать две цифры
        time = f"0{time}"
    if not re.match(r"\d\d\.\d\d", time): # Проверяем, не введена ли дата в нужном нам формате
        months = {
            "января": ".01", "февраля": ".02", "марта": ".03", "апреля": ".04",
            "мая": ".05", "июня": ".06", "июля": ".07", "августа": ".08",
            "сентября": ".09", "октября": ".10", "ноября": ".11", "декабря": ".12"
        }
        for word, num in months.items():
            if word in time:
                time = re.sub(fr"\s?{word}", num, time)
    if not re.search(r"\d\d:\d\d", time): # Проверяем, ввёл ли пользователь время
        time += " 00:00"
    if not re.search(r"\d{4}", time): # Проверяем, указал ли пользователь год
        try:
            timeObject = datetime.strptime(time, "%d.%m %H:%M") # Предполагается, что к этому моменту формат даты правильный, исключая отсутствие года
            validated = True # Если преобразование выше сработало, формат точно станет валидным после добавления года
        except ValueError:
            return None
        timeObject = datetime(datetime.today().year, timeObject.month, timeObject.day, timeObject.hour, timeObject.minute) # Костыль для изменения года у объекта datetime
        timeList = time.split()
        if datetime.today() < timeObject:
            timeList[0] += f".{str(datetime.today().year)}"
        else:
            timeList[0] += f".{str(datetime.today().year + 1)}" # Если в этом году введённое время уже прошло, устанавливаем дедлайн на то же время в следующем году
        time = " ".join(timeList)
    if validated:
        return time
    else:
        try:
            datetime.strptime(time, "%d.%m.%Y %H:%M") # Проверяем формат на валидность
            return time
        except ValueError:
            return None

def ignore_case_collation(value1_: str, value2_: str):
    """Добавляет поддержку регистронезависимого сравнения кириллицы в SQLite."""
    if value1_.lower() == value2_.lower():
        return 0
    elif value1_.lower() < value2_.lower():
        return -1
    else:
        return 1

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

main()
