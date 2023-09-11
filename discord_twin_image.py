from dotenv import load_dotenv
import os 
import json
import pandas as pd
import discord 
import uuid
import asyncio
load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
class DiscordDataBot(discord.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.input_df = pd.read_csv("output.csv")
        if not os.path.isfile("results.csv"):
            pd.DataFrame(columns=["user_id", "uuid", "rating"]).to_csv("results.csv", index=False)        
        self.result_df = pd.read_csv("results.csv")        
        self.user_history = {}

    def get_random_row(self):
        random_row = self.input_df.sample()
        random_row_json = json.loads(random_row.to_json(orient="records"))[0]
        return random_row_json
    
    async def save_to_csv(self, user_id, uuid, rating):
        #Replace with database call as needed
        new_row = {"user_id": user_id, "uuid": uuid, "rating": rating}
        self.result_df = pd.concat([self.result_df, pd.DataFrame([new_row])], ignore_index=True)
        self.result_df.to_csv("results.csv", index=False)

class FeedbackView(discord.ui.View):
    def __init__(self, ctx, id, current_label = "", original_message_id = 0):
        super().__init__(timeout=1200)
        self.ctx = ctx
        self.id = id
        self.current_label = current_label
        self.original_message_id = original_message_id

        # Check states and update the styles accordingly
        rating = self.ctx.bot.user_history[self.ctx.author.id][self.id]["rating"] if self.ctx.author.id in self.ctx.bot.user_history else 0
        both_good_style = discord.ButtonStyle.success if rating == 2 else discord.ButtonStyle.secondary
        image_good_prompt_bad_style = discord.ButtonStyle.success if rating == 1 else discord.ButtonStyle.secondary
        both_bad_style = discord.ButtonStyle.danger if rating == 0 else discord.ButtonStyle.secondary

        self.both_bad_button = discord.ui.Button(label="", emoji="❌", style=both_bad_style, row=0)
        self.both_bad_button.callback = self.both_bad
        self.add_item(self.both_bad_button)

        self.image_good_prompt_bad_button = discord.ui.Button(label="", emoji="😶", style=image_good_prompt_bad_style, row=0)
        self.image_good_prompt_bad_button.callback = self.image_good_prompt_bad
        self.add_item(self.image_good_prompt_bad_button)

        self.both_good_button = discord.ui.Button(label="", emoji="✅", style=both_good_style, row=0)
        self.both_good_button.callback = self.both_good
        self.add_item(self.both_good_button)
        # self.report_button = discord.ui.Button(label="", emoji="🚫", style=discord.ButtonStyle.secondary, row=0)
        # self.report_button.callback = self.report
        # self.add_item(self.report_button)

        # self.skip_button = discord.ui.Button(style=discord.ButtonStyle.secondary, label="", emoji="⏭️", row=0)
        # self.skip_button.callback = self.skip
        # self.add_item(self.skip_button)

    async def skip(self, interaction: discord.Interaction):
        await interaction.response.send_message("Skipping image pair, sending next one...")
        await send_image_pair(self.ctx) 

    async def both_good(self, interaction: discord.Interaction):    
        await interaction.response.defer()

        self.both_good_button.style = discord.ButtonStyle.blurple
        self.image_good_prompt_bad_button.style = discord.ButtonStyle.secondary
        self.both_bad_button.style = discord.ButtonStyle.secondary
        await interaction.message.edit(view=self)
        bot.user_history[self.ctx.author.id][self.id]["rating"] = 2
        await bot.save_to_csv(self.ctx.author.id, self.id, 2)
        await interaction.message.delete()
        await send_image_pair(self.ctx)

    async def image_good_prompt_bad(self, interaction: discord.Interaction):    
        await interaction.response.defer()

        self.image_good_prompt_bad_button.style = discord.ButtonStyle.blurple
        self.both_good_button.style = discord.ButtonStyle.secondary
        self.both_bad_button.style = discord.ButtonStyle.secondary
        await interaction.message.edit(view=self)
        bot.user_history[self.ctx.author.id][self.id]["rating"] = 1
        await bot.save_to_csv(self.ctx.author.id, self.id, 1)
        await interaction.message.delete()
        await send_image_pair(self.ctx)

    async def both_bad(self, interaction: discord.Interaction):
        await interaction.response.defer()

        self.both_bad_button.style = discord.ButtonStyle.blurple
        self.image_good_prompt_bad_button.style = discord.ButtonStyle.secondary
        self.both_good_button.style = discord.ButtonStyle.secondary
        await interaction.message.edit(view=self)

        bot.user_history[self.ctx.author.id][self.id]["rating"] = 0
        await bot.save_to_csv(self.ctx.author.id, self.id, 0)
        await interaction.message.delete()
        await send_image_pair(self.ctx)

    async def report(self, interaction: discord.Interaction):
        await interaction.response.send_message("Image pair reported")
        await send_image_pair(self.ctx)

if __name__ == '__main__':
    intents = discord.Intents.default()
    intents.message_content = True 
    bot = DiscordDataBot(intents=intents)

    @bot.event
    async def on_ready():
        print(f"We have logged in as {bot.user}")

    @bot.command(description="Get Image Pair")
    async def start_running(ctx):
        await send_image_pair(ctx)

    async def send_image_pair(ctx):
        id = f"{ctx.author.id}_{uuid.uuid4()}"
        image_pair = bot.get_random_row()
        print(image_pair)
        if ctx.author.id not in bot.user_history:
            bot.user_history[ctx.author.id] = {}

        bot.user_history[ctx.author.id][id] = {
            "user_id" : ctx.author.id,
            "uuid": image_pair["uuid"],
            "image_0_url": image_pair["image_0_url"],
            "image_0_description": image_pair["image_0_description"],
            "image_1_url": image_pair["image_1_url"],
            "image_1_description": image_pair["image_1_description"],
            "instructions": image_pair["instructions"], 
            "rating": -1, 
        }

        await ctx.respond(
            content=f'{ctx.author.mention}, please vote on if this is a valid motion description or not\n{image_pair["image_0_url"]}\n{image_pair["image_1_url"]}\nInstructions: {image_pair["instructions"]}', 
            view=FeedbackView(ctx, id=id)
        )        

    print("Running...")
    bot.run(DISCORD_TOKEN)