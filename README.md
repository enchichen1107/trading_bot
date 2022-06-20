# 🌱 韭菜是割還是哥！？
### 🌱 🌱 從零開始打造雲端交易機器人🤖 + dashboard app 👀

這裡是比特幣大盤分析、交易策略回測、交易機器人實作、dashboard app實作之code集中區

**各檔案內容涵蓋的code如下述(依字母順位做排序)**：
 - **app**：以streamlit製作的dashboard
 - **backtest**：交易策略回測歷史資料
 - **bot**：bot1和bot2內容相似，僅策略參數具差異，放兩份是因為它們各自在不同的AWS EC2 t2.micro上運作，若欲參考，看其中一份即可
 - **btc_price_overview**：近三年的比特幣大盤分析
 - **fetch_historical_price**：以binance api撈取回測用的資料 
 - **symbol_fullname_convert**：DB中有一張table記錄著交易標的簡稱與全名對照，該table內資料是透過這份code產出

**以下是這份專案的相關重要連結**
- [非常完整的開發文件說明](https://hackmd.io/@BU35KookTOibU7DKFYvFFw/rk4CIxMt9)
- [dashboard成品](http://15.165.161.231:8501/)
  - 我用了最新版的streamlit app，目前測試mac用chrome、iphone 11以上用chrome、android用chrome，都可順利開啟此app，但windows目前會出錯，官方表示有在修復，若開不了請先看底下影片demo 
  - 因近日交易低迷，各機器人僅有一日有做到交易(美國加息會議那天)，故有先放一些pseudo data來demo app功能
- [雲端交易機器人影片demo](https://www.youtube.com/watch?v=CaWtj_EcH_4)
- [dashboard app影片demo](https://www.youtube.com/watch?v=CyIGc61JsNw)