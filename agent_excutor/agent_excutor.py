from langchain_classic.runnables import hub
from config_utils import api_key,base_url,api_tavily
from langchain.agents import create_agent
from langchain_openai.chat_models import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults

tools = [TavilySearchResults(api_key=api_tavily,max_results=1)]

# Get the prompt to use - you can modify this!
prompt = hub.pull ("hwchase17/openai-functions-agent")

llm = ChatOpenAI(
            model="Pro/MiniMaxAI/MiniMax-M2.5",
            api_key=api_key,
            base_url=base_url,
            streaming=True
        )

agent = create_agent(prompt, tools, llm)


# define graph state





