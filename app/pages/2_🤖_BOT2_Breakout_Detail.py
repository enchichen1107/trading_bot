import helper

df = helper.fetch_trade(bot = 2)
asset = helper.fetch_asset(bot = 2)

bot2 = helper.layout(bot = 2, df = df, asset = asset)
bot2.start_demo()