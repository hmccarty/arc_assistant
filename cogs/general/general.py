""""
Modified by Harrison McCarty - Autonomous Robotics Club of Purdue
Copyright © Krypton 2021 - https://github.com/kkrypt0nn

Description:
Holds common utility commands.
"""

import json
import os
import random
import sys
import sqlite3
import datetime as dt
import dateparser as dp
from typing import List, Tuple, Union

from helpers.db_manager import BacklogModel, RoleMenuModel

import disnake
from disnake.ext import commands, tasks

if not os.path.isfile("config.json"):
    sys.exit("'config.json' not found! Please add it and try again.")
else:
    with open("config.json") as file:
        config = json.load(file)

class Reminder(object):
    def __init__(self, ctx: commands.Context, members: [disnake.Member], reason: str, time: dt.datetime):
        self.ctx = ctx
        self.members = members
        self.time = time
        self.reason = reason
    
    async def send_msg(self):
        refids = ", ".join(f"<@{x.id}>" for x in self.members)
        await self.ctx.send(f"{refids} {self.reason}")

    def is_ready(self):
        return self.time < dt.datetime.now()

class General(commands.Cog, name="general"):
    def __init__(self, bot):
        self.bot = bot
        self.reminders = []

    def open_db(self):
        return sqlite3.connect(config["db"], timeout=10)

    @commands.command(name="status")
    async def info(self, ctx: commands.Context):
        """
        Get some useful (or not) information about the bot.
        """

        await ctx.send("Still alive lol")

    @commands.command(name="..")
    async def ellipses(self, ctx: commands.Context):
        """
        Reinforce the dramatic atmosphere.
        """

        await ctx.send("*GASPS*")

    @tasks.loop(seconds=10)
    async def send_reminders(self):
        for reminder in self.reminders:
            if reminder.is_ready():
                self.reminders.remove(reminder)
                await reminder.send_msg()

        if len(self.reminders) == 0:
            self.send_reminders.stop()

    @commands.command(name="remind")
    async def remind(self, ctx: commands.Context, members: commands.Greedy[disnake.Member],
        reason: str, timeinfo: str):
        """
        Reminds the list of members of a custom message at a set time.
        'timeinfo' follows example format: "Jan 02 01:30 AM"
        """

        rtime = dp.parse(timeinfo)
        self.reminders.append(Reminder(ctx, members, reason, rtime))
        await ctx.send(f"Reminder set for {rtime.strftime('%b %d %I:%M %p')}")
        if not self.send_reminders.is_running():
            self.send_reminders.start()

    @commands.command(name="poll")
    async def poll(self, ctx: commands.Context, *, title: str):
        """
        Create a poll where members can vote.
        """
        embed = disnake.Embed(title=f"{title}", color=0x42F56C)
        embed.set_footer(
            text=f"Poll created by: {ctx.message.author} • React to vote!"
        )
        embed_message = await ctx.send(embed=embed)
        await embed_message.add_reaction("👍")
        await embed_message.add_reaction("👎")
        await embed_message.add_reaction("🤷")

    @commands.command(name="8ball")
    async def eight_ball(self, ctx: commands.Context, *, question: str = ''):
        """
        Ask any question to the bot.
        """
        answers = [
            "It is certain.",
            "It is decidedly so.",
            "You may rely on it.",
            "Without a doubt.",
            "Yes - definitely.",
            "As I see, yes.",
            "Most likely.",
            "Outlook good.",
            "Yes.",
            "Signs point to yes.",
            "My reply is no.",
            "My sources say no.",
            "Outlook not so good.",
            "Very doubtful.",
        ]

        refid = "<@" + str(ctx.message.author.id) + "> "
        await ctx.send(refid + answers[random.randint(0, len(answers) - 1)])

    @commands.command(name="backlog")
    async def backlog(self, ctx: commands.Context):
        """
        Print current bot backlog.
        """
        
        backlog_items = BacklogModel.get_all()
        if len(backlog_items) > 0:
            msg = ""
            for i in range(len(backlog_items)):
                msg += f"{i+1}. {backlog_items[i].item}\n\n"

            embed = disnake.Embed(title="My backlog", description=msg)
            await ctx.send(embed=embed)
        else:
            await ctx.send("No items in the backlog!")

    @commands.command(name="todo")
    async def todo(self, ctx: commands.Context, item: str):
        """
        Adds item to backlog.
        """

        if ctx.message.author.id in config["owners"]:
            BacklogModel.add(item)
            await ctx.send("Added item to backlog.")
        else:
            embed = disnake.Embed(
                title="Error!",
                description="You don't have the permission to use this command.",
                color=0xE02B2B,
            )
            await ctx.send(embed=embed)

    @commands.command(name="finished")
    async def finished(self, ctx: commands.Context, item: str):
        """
        Removes item from backlog.
        """

        if ctx.message.author.id in config["owners"]:
            result = None
            with self.open_db() as c:
                if BacklogModel.find_and_remove(item):
                    await ctx.send("Removed item from backlog.")
                else:
                    await ctx.send("Couldn't find item in backlog.")
        else:
            raise commands.MissingPermissions([])

    @commands.command(name="rolemenu")
    async def rolemenu(self, ctx: commands.Context, title: str,
        roles: commands.Greedy[disnake.Role], *, emojis: str):
        """
        Allow users to set roles through reaction.
        """

        emojis = emojis.split(' ')
        if len(roles) != len(emojis):
            raise commands.UserInputError(message="Must have equal roles and emojis")
        
        menu_desc = "React to give yourself a role. \n\n"
        for emoji, role in zip(emojis, roles):
            menu_desc += "{}: `{}`\n".format(emoji, role)

        embed = disnake.Embed(title=title, description=menu_desc, color=0x42F56C)
        menu = await ctx.send(embed=embed)

        for emoji, role in zip(emojis, roles):
            RoleMenuModel.add_option(menu.id, ctx.guild.id, role.name, emoji)
            await menu.add_reaction(emoji)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: disnake.RawReactionActionEvent):
        if payload.member is None or payload.member.bot:
            return

        options = RoleMenuModel.get(payload.message_id, payload.guild_id)
        if len(options) > 0:
            guild = self.bot.get_guild(payload.guild_id)
            for option in options:
                if option.emoji == str(payload.emoji.name):
                    role = disnake.utils.get(guild.roles, name=option.role)
                    if role not in payload.member.roles:
                        await payload.member.add_roles(role)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: disnake.RawReactionActionEvent):
        options = RoleMenuModel.get(payload.message_id, payload.guild_id)
        if len(options) > 0:
            guild = self.bot.get_guild(payload.guild_id)
            member = guild.get_member(payload.user_id)
            if member is None:
                return
            for option in options:
                if option.emoji == str(payload.emoji.name):

                    role = disnake.utils.get(guild.roles, name=option.role)
                    if role in member.roles:
                        await member.remove_roles(role)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: disnake.RawReactionActionEvent):
        RoleMenuModel.delete_menu(payload.message_id, payload.guild_id)

def setup(bot):
    bot.add_cog(General(bot))
