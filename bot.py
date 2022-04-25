from vkbottle.bot import Bot, BotLabeler, Message
from config import token
import sqlite3

def main():
    @bot.on.message(text="/добавить <deadline> на <time>")
    @bot.on.private_message(text="добавить <deadline> на <time>")
    async def setDeadline(message: Message, deadline: str, time: str):
        row = {"chat": message.peer_id, "deadline": deadline, "time": time}
        if message.from_id == message.peer_id:
            row["isGroup"] = False
        else:
            row["isGroup"] = True
        cur.execute("INSERT INTO Deadlines VALUES(:chat, :deadline, :time, :isGroup);", row)
        database.commit()
        await message.answer(f"Дедлайн <<{deadline}>> установлен на {time}")

    @bot.on.message(text="/удалить <deadline>")
    @bot.on.private_message(text="удалить <deadline>")
    async def removeDeadline(message: Message, deadline: str):
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
        cur.execute("DELETE FROM Deadlines WHERE chat=?;", (message.peer_id,))
        database.commit()
        await message.answer("Все дедлайны удалены")

    @bot.on.message(text="/дедлайны")
    @bot.on.private_message(text="дедлайны")
    async def sendDeadlines(message: Message):
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

def ignore_case_collation(value1_, value2_): # Добавляет поддержку регистронезависимого сравнения кириллицы в SQLite
    if value1_.lower() == value2_.lower():
        return 0
    elif value1_.lower() < value2_.lower():
        return -1
    else:
        return 1

bot = Bot(token)
bot.labeler.vbml_ignore_case = True
bot.labeler.load(BotLabeler())

database = sqlite3.connect("deadlines.db")
database.create_collation("NOCASE", ignore_case_collation)
cur = database.cursor()
cur.execute("""CREATE TABLE IF NOT EXISTS Deadlines(
    chat INT,
    deadline TEXT,
    time TEXT,
    isGroup INT
);""")
database.commit()

main()
