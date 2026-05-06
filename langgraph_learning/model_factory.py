from config_utils import api_key,base_url
from langchain_openai import ChatOpenAI
from langchain_openai.embeddings import OpenAIEmbeddings

MiniMax_Model = ChatOpenAI(
    model="Pro/MiniMaxAI/MiniMax-M2.5",
    api_key=api_key,
    base_url=base_url,
    streaming=True
)

embedding_model = OpenAIEmbeddings(
    model="Qwen/Qwen3-Embedding-8B",
    api_key=api_key,
    base_url=base_url,
)
