""""
Created by Harrison McCarty - Autonomous Robotics Club of Purdue

Description:
Enables on-server currency.
"""

import json
import os
import sys
import sqlite3

import discord
from discord.ext import commands

if not os.path.isfile("config.json"):
    sys.exit("'config.json' not found! Please add it and try again.")
else:
    with open("config.json") as file:
        config = json.load(file)

con = sqlite3.connect(config["db"])
cur = con.cursor()
cur.execute('CREATE TABLE IF NOT EXISTS currency(member INT, balance INT)')
con.commit()


class Currency(commands.Cog, name="currency"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="thanks", aliases=['pay'])
    async def thanks(self, context, *, member: discord.Member = None):
        """
        Grants member a single ARC coin.
        """
        if member is None:
            author_ref = "<@" + str(context.message.author.id) + ">"
            await context.send(
                author_ref + " you didn't say who you're sending money too."
            )
            return
        elif member.id == context.message.author.id:
            author_ref = "<@" + str(context.message.author.id) + ">"
            await context.send(
                author_ref + " stop trying to print ARC coins."
            )
            return

        result = cur.execute(
            "SELECT * FROM currency WHERE member=(?)", (member.id,)
        ).fetchone()
        if result is None:
            cur.execute(
                "INSERT INTO currency VALUES (?, ?)", (member.id, 1)
            )
        else:
            cur.execute(
                "UPDATE currency SET balance=(?) WHERE member=(?)",
                (result[1] + 1, result[0])
            )
        con.commit()

        member_ref = "<@" + str(member.id) + ">"
        await context.send("Gave +1 ARC Coins to {}".format(member_ref))

    @commands.command(name="balance")
    async def balance(self, context):
        """
        Prints current balance of ARC coins.
        """
        name = context.message.author.name
        id = context.message.author.id

        result = cur.execute(
            "SELECT * FROM currency WHERE member=(?)", (id,)).fetchone()
        if result is None:
            balance = 0
        else:
            balance = result[1]

        await context.send("Current balance for {}: {}".format(name, balance))

    @commands.command(name="leaderboard")
    async def leaderboard(self, context):
        """
        Prints top 5 members with most amount of ARC coins.
        """
        results = cur.execute(
            "SELECT * FROM currency ORDER BY balance desc LIMIT 5").fetchall()
        if len(results) == 0:
            leaderboard = "Everybody is broke"
        else:
            leaderboard = "ARC Coin Leaderboard\n"
            pos = 1
            for result in results:
                member_ref = "<@" + str(result[0]) + ">"
                leaderboard += "{}: {} with {} coins\n".format(
                    pos, member_ref, result[1]
                )
                pos += 1

        await context.send(leaderboard)


def setup(bot):
    bot.add_cog(Currency(bot))