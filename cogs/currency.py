""""
Created by Harrison McCarty - Autonomous Robotics Club of Purdue

Description:
Enables on-server currency.
"""

import json
import os
import sys
import sqlite3
from datetime import datetime as dt

import discord
from discord.ext import commands

from helpers import arcdle

if not os.path.isfile("config.json"):
    sys.exit("'config.json' not found! Please add it and try again.")
else:
    with open("config.json") as file:
        config = json.load(file)


class Currency(commands.Cog, name="currency"):
    def __init__(self, bot):
        self.bot = bot
        self.arcdle_sol = arcdle.pick_solution()
        self.sol_date = dt.now()
        with self.open_db() as c:
            c.execute("CREATE TABLE IF NOT EXISTS currency(member INT, balance INT)")
            c.execute("CREATE TABLE IF NOT EXISTS arcdle(user INT, origin INT, game INT, visible TEXT, hidden TEXT, status INT)")

    def open_db(self):
        return sqlite3.connect(config["db"], timeout=10)

    @commands.command(name="thanks", aliases=["pay"])
    async def thanks(self, ctx: commands.Context, member: discord.Member):
        """
        Grants member a single ARC coin.
        """

        if member.id == ctx.message.author.id:
            refid = "<@" + str(ctx.message.author.id) + ">"
            await ctx.send(refid + " stop trying to print ARC coins.")
            return

        try:
            with self.open_db() as c:
                result = c.execute(
                    "SELECT * FROM currency WHERE member=(?)", (member.id,)
                ).fetchone()
                if result is None:
                    c.execute("INSERT INTO currency VALUES (?, ?)", (member.id, 1))
                else:
                    c.execute(
                        "UPDATE currency SET balance=(?) WHERE member=(?)",
                        (result[1] + 1, result[0]),
                    )

                refid = "<@" + str(member.id) + ">"
                await ctx.send("Gave +1 ARC Coins to {}".format(refid))
        except sqlite3.Error as e:
            await ctx.send("Unable to produce coin: {}".format(e.args[0]))

    @commands.command(name="balance")
    async def balance(self, ctx: commands.Context):
        """
        Prints current balance of ARC coins.
        """
        name = ctx.message.author.name
        id = ctx.message.author.id

        with self.open_db() as c:
            result = c.execute(
                "SELECT * FROM currency WHERE member=(?)", (id,)
            ).fetchone()

            if result is None:
                balance = 0
            else:
                balance = result[1]

            await ctx.send("Current balance for {}: {}".format(name, balance))

    @commands.command(name="leaderboard")
    async def leaderboard(self, ctx: commands.Context):
        """
        Prints top 5 members with most amount of ARC coins.
        """

        with self.open_db() as c:
            results = c.execute(
                "SELECT * FROM currency ORDER BY balance desc LIMIT 5"
            ).fetchall()

        if len(results) == 0:
            leaderboard = "Everybody is broke"
        elif ctx.guild is not None:
            leaderboard = "**ARC Coin Leaderboard**\n"
            pos = 1
            for result in results:
                member = ctx.guild.get_member(result[0])
                if member is not None:
                    if member.nick is not None:
                        name = member.nick
                    else:
                        name = member.name

                    if result[1] == 1:
                        leaderboard += "{}: {} with {} coin\n".format(
                            pos, name, result[1]
                        )
                    else:
                        leaderboard += "{}: {} with {} coins\n".format(
                            pos, name, result[1]
                        )
                pos += 1
        else:
            leaderboard = "Command can only be used in a guild."
        await ctx.send(leaderboard)

    async def handle_message(self, msg: discord.Message):
        """
        Called when a direct message is received for arcdle.
        """

        msg_content = msg.content.strip().lower()
        if len(msg_content) == 5 and msg_content.isalpha():
            with self.open_db() as c:
                result = c.execute(
                    "SELECT * FROM arcdle WHERE user=(?)", (msg.author.id,)
                ).fetchone()
            id, origin, game, visible, hidden, status = result

            if self.sol_date.date != dt.now().date:
                self.arcdle_sol = arcdle.pick_solution()
                self.sol_date = dt.now()
            sol = self.arcdle_sol

            prev_visible_guesses = visible.split(",")
            prev_hidden_guesses = hidden.split(",")

            hidden_guess = ""
            visible_guess = ""
            correct_cnt = 0

            # Remove perfect matches
            for i in range(5):
                if msg_content[i] == self.arcdle_sol[i]:
                    sol = sol[:i] + sol[i+1:]

            # Display partial and perfect matches
            for i in range(5):
                if msg_content[i] == self.arcdle_sol[i]:
                    correct_cnt += 1
                    visible_guess += f"__**{msg_content[i]}**__ "
                    hidden_guess += ":green_square: "
                elif msg_content[i] in sol:
                    sol = sol.replace(msg_content[i], "", 1)
                    visible_guess += f"**{msg_content[i]}** "
                    hidden_guess += ":yellow_square: "
                else:
                    visible_guess += f"{msg_content[i]} "
                    hidden_guess += ":black_large_square: "

            if prev_visible_guesses[0] != "":
                visible_guesses = prev_visible_guesses + [visible_guess]
            else:
                visible_guesses = [visible_guess]
            
            if prev_hidden_guesses[0] != "":
                hidden_guesses = prev_hidden_guesses + [hidden_guess]
            else:
                hidden_guesses = [hidden_guess]

            status = 0
            if correct_cnt == 5:
                status = 1
            elif len(visible_guesses) == 6:
                status = 2

            winning_amt = 0.0
            if status == 1:
                winning_amt = 0.5
                board_desc = f"<@{id}> guessed in {len(visible_guesses)} attempt(s), " + \
                    f"earning {winning_amt} ARC coins\n\n"
            elif status == 2:
                winning_amt = 0.05
                board_desc = f"<@{id}> failed to guess in {len(visible_guesses)} attempt(s), " + \
                    f"earning {winning_amt} ARC coins\n\n"
            else:
                board_desc = f"{6-len(visible_guesses)}/6 guesses remain\n\n"

            if status != 0:
                with self.open_db() as c:
                    result = c.execute(
                        "SELECT * FROM currency WHERE member=(?)", (id,)
                    ).fetchone()
                    if result is None:
                        c.execute("INSERT INTO currency VALUES (?, ?)", (id, winning_amt))
                    else:
                        c.execute(
                            "UPDATE currency SET balance=(?) WHERE member=(?)",
                            (result[1] + winning_amt, result[0]),
                        )

                public_desc = board_desc
                for i in range(len(hidden_guesses)):
                    public_desc += hidden_guesses[i]
                    if i < 5:
                        public_desc += "\n\n"

                guild = self.bot.get_guild(config["server_id"])
                public = discord.Embed(title=f"{msg.author.name}'s ARCdle", description=public_desc)
                await guild.get_channel(origin).send(embed=public)

            for i in range(len(visible_guesses)):
                board_desc += visible_guesses[i]
                if i < 5:
                    board_desc += "\n\n"
            
            if status == 0:
                for i in range(len(visible_guesses), 6):
                    board_desc += "\_ \_ \_ \_ \_"
                    if i < 5:
                        board_desc += "\n\n"
            board = discord.Embed(title="ARCdle", description=board_desc)

            old_board = await msg.channel.fetch_message(game)
            await old_board.edit(embed=board)

            visible_guesses = ",".join(visible_guesses)
            hidden_guesses = ",".join(hidden_guesses)

            with self.open_db() as c:
                c.execute(
                    """
                    UPDATE arcdle SET visible=(?), hidden=(?), status=(?)
                    WHERE user=(?);
                    """,
                    (visible_guesses, hidden_guesses, status, msg.author.id),
                )

        else:
            await msg.channel.send("Guess must be a 5 letter word.")

    async def in_arcdle_game(self, id: int):
        """
        Checks whether user has started an arcdle game.
        """

        with self.open_db() as c:
            result = c.execute(
                "SELECT * FROM arcdle WHERE user=(?)", (id,)
            ).fetchone()
        
        return result is not None and result[5] == 0

    @commands.command(name="arcdle")
    async def arcdle(self, ctx: commands.Context):
        """
        Starts a game of arcdle for some coins
        """

        id = ctx.message.author.id

        try:
            with self.open_db() as c:
                result = c.execute(
                    "SELECT * FROM arcdle WHERE user=(?)", (id,)
                ).fetchone()
        except sqlite3.Error as e:
            await ctx.send("Unable to play: {}".format(e.args[0]))
            return

        if result is not None:
            refid = "<@" + str(id) + ">"
            if result[5] > 0:
                await ctx.send(refid + " you've already played today, come back tomorrow.")
            else:
                await ctx.send(refid + " you already started a game, check your DMs.")
        else:
            board_desc = "6/6 guesses remain \n\n"
            for i in range(6):
                board_desc += "\_ \_ \_ \_ \_"
                if i < 5:
                    board_desc += "\n\n"
            board = discord.Embed(title="ARCdle", description=board_desc)
            game = await ctx.message.author.send(embed=board)
            
            with self.open_db() as c:
                result = c.execute(
                    "INSERT INTO arcdle VALUES (?, ?, ?, ?, ?, ?)",
                    (id, ctx.channel.id, game.id, "", "", 0)
                )

    @commands.command(name="set")
    async def set(self, ctx: commands.Context, member: discord.Member, amount: int):
        """
        Deletes cached verification information.
        """

        if member is None:
            refid = "<@" + str(ctx.message.author.id) + ">"
            await ctx.send(refid + " you didn't say who you're sending money too.")
        elif ctx.message.author.id in config["owners"]:
            with self.open_db() as c:
                result = c.execute(
                    "SELECT * FROM currency WHERE member=(?)", (member.id,)
                ).fetchone()
                if result is None:
                    c.execute("INSERT INTO currency VALUES (?, ?)", (member.id, amount))
                else:
                    c.execute(
                        "UPDATE currency SET balance=(?) WHERE member=(?)",
                        (amount, member.id),
                    )

            await ctx.send(
                "{} set {} balance to {}".format(
                    "<@" + str(ctx.message.author.id) + ">",
                    "<@" + str(member.id) + ">",
                    amount,
                )
            )
        else:
            raise commands.MissingPermissions([])


def setup(bot):
    bot.add_cog(Currency(bot))
