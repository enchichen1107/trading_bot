import helper

df = helper.fetch_trade(bot = 1)
asset = helper.fetch_asset(bot = 1)

bot1 = helper.layout(bot = 1, df = df, asset = asset)
bot1.start_demo()